from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
import sys
import os
from datetime import datetime
import json
import re
import PyPDF2
import pdfplumber
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_, Integer
from db.session import get_db
from db.models import DoctorReport

# Import schemas
from schemas.doctor_router import (
    DoctorVerificationRequest,
    DoctorSearchRequest,
    VerificationResult,
    SearchResult,
    GetReportsResponse,
    DoctorReportResponse
)

# Import route constants
from config.route_config import (
    VERIFY_DOCTOR,
    SEARCH_DOCTOR,
    GET_SPECIALTIES,
    GET_INSURANCE_NETWORKS,
    EXTRACT_PDF,
    HEALTH_CHECK,
    GET_REPORTS
)

# Add helpers to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'helpers'))
from helpers.funtion import search_doctor_info, DoctorInfoScraper

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/doctor",
    tags=["doctor"],
    responses={404: {"description": "Not found"}}
)

# Medical specialties constant
SPECIALTIES = [
    'Allergy and Immunology', 'Anesthesiology', 'Cardiology', 'Dermatology',
    'Emergency Medicine', 'Endocrinology', 'Family Medicine', 'Gastroenterology',
    'General Surgery', 'Geriatric Medicine', 'Hematology', 'Infectious Disease',
    'Internal Medicine', 'Nephrology', 'Neurology', 'Obstetrics and Gynecology',
    'Oncology', 'Ophthalmology', 'Orthopedic Surgery', 'Otolaryngology (ENT)',
    'Pathology', 'Pediatrics', 'Physical Medicine and Rehabilitation',
    'Plastic Surgery', 'Psychiatry', 'Pulmonology', 'Radiology', 'Rheumatology',
    'Sports Medicine', 'Urology', 'Vascular Surgery'
]

INSURANCE_NETWORKS = [
    'Aetna', 'Anthem Blue Cross', 'Blue Cross Blue Shield', 'Cigna', 'Humana',
    'Kaiser Permanente', 'Medicare', 'Medicaid', 'UnitedHealthcare', 'Oscar Health',
    'Molina Healthcare', 'Centene', 'WellCare', 'Magellan Health', 'Tricare'
]

# Helper functions
def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names"""
    if not name1 or not name2:
        return 0.0
    
    # Simple word-based similarity
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def calculate_address_similarity(addr1: str, addr2: str) -> float:
    """Calculate similarity between two addresses"""
    if not addr1 or not addr2:
        return 0.0
    
    # Simple word-based similarity for addresses
    words1 = set(addr1.lower().replace(',', '').split())
    words2 = set(addr2.lower().replace(',', '').split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

async def analyze_verification(request, scraped_data: Dict) -> Dict:
    """
    Analyze verification results with simplified field-by-field comparison
    """
    # Get best matching provider from NPI data
    best_provider = get_best_matching_provider(request, scraped_data)
    
    # Verify each input field in the new simplified format
    verification_results = {
        "fullName": verify_full_name(request.fullName, scraped_data, best_provider),
        "specialty": verify_specialty(request.specialty, scraped_data, best_provider),
        "address": verify_address(request.address, scraped_data, best_provider),
        "phoneNumber": verify_phone_number(request.phoneNumber, scraped_data, best_provider),
        "licenseNumber": verify_license_number(request.licenseNumber, scraped_data, best_provider, request.specialty),
        "insuranceNetworks": verify_insurance_networks(request.insuranceNetworks, scraped_data, best_provider),
        "servicesOffered": verify_services_offered(request.servicesOffered, scraped_data, best_provider)
    }
    
    return verification_results

def get_best_matching_provider(request, scraped_data: Dict):
    """Get the best matching provider from scraped data"""    
    try:
        # Handle the actual NPI API response structure
        npi_response = scraped_data.get("npi_data", {})
        providers = npi_response.get("results", [])
        
        if not providers:
            return None
        
        best_match = None
        best_score = 0
        
        for provider in providers:
            if not isinstance(provider, dict):
                continue
                
            # Calculate name similarity
            basic_info = provider.get('basic', {})
            if isinstance(basic_info, dict):
                provider_name = f"{basic_info.get('first_name', '')} {basic_info.get('last_name', '')}".strip()
            else:
                # Fallback for different data structure
                provider_name = provider.get('name', '')
            
            name_score = calculate_name_similarity(request.fullName, provider_name) if provider_name else 0.0
            
            # Check specialty match - handle None specialty
            specialty_score = 0.0
            if request.specialty and request.specialty.strip():
                provider_specialties = []
                taxonomies = provider.get("taxonomies", [])
                
                if isinstance(taxonomies, list):
                    for tax in taxonomies:
                        if isinstance(tax, dict):
                            desc = tax.get("desc", "")
                            if desc:
                                provider_specialties.append(desc)
                
                if provider_specialties:
                    specialty_match = any(request.specialty.lower() in spec.lower() for spec in provider_specialties if spec)
                    specialty_score = 1.0 if specialty_match else 0.0
            
            # Combined score
            combined_score = (name_score * 0.7) + (specialty_score * 0.3)
            
            if combined_score > best_score and combined_score > 0.5:  # Lower threshold for better matching
                best_score = combined_score
                best_match = provider
        
        return best_match
    
    except Exception as e:
        logger.error(f"Error in get_best_matching_provider: {str(e)}")
        return None

def verify_full_name(input_name: str, scraped_data: Dict, best_provider) -> Dict:
    """Verify full name against scraped data"""
    result = {
        "input_field_a": input_name if input_name else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        found_name = None
        data_source = None
        
        # First, try NPI Registry
        if best_provider and isinstance(best_provider, dict):
            basic_info = best_provider.get("basic", {})
            
            if isinstance(basic_info, dict):
                found_name = f"{basic_info.get('first_name', '')} {basic_info.get('last_name', '')}".strip()
                if found_name:
                    data_source = "NPI Registry"
        
        # If no name in NPI, try other scraped sources
        if not found_name and scraped_data.get("name"):
            found_name = scraped_data.get("name")
            data_source = "Provider Directories"
        
        # Try Google Places data
        if not found_name:
            practice_locations = scraped_data.get("practice_locations", [])
            if isinstance(practice_locations, list) and practice_locations:
                for location in practice_locations:
                    if isinstance(location, dict) and location.get("doctor_name"):
                        found_name = location["doctor_name"]
                        data_source = "Google Places"
                        break
        
        # Set results
        if found_name:
            result["scraped_data_field_a"] = found_name
            result["scraped_from"] = data_source
            
            if input_name and input_name.strip():
                similarity = calculate_name_similarity(input_name, found_name)
                result["matches"] = similarity >= 0.8
            else:
                result["matches"] = None  # No input to compare
        
        logger.debug(f"Name verification: input='{input_name}', found='{found_name}', source='{data_source}'")
                
    except Exception as e:
        logger.error(f"Error in verify_full_name: {str(e)}")
    
    return result

def verify_specialty(input_specialty: str, scraped_data: Dict, best_provider) -> Dict:
    """Verify specialty against scraped data"""
    result = {
        "input_field_a": input_specialty if input_specialty else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        found_specialty = None
        data_source = None
        
        # First, try NPI Registry
        if best_provider and isinstance(best_provider, dict):
            taxonomies = best_provider.get("taxonomies", [])
            if taxonomies and isinstance(taxonomies, list):
                # Get primary specialty first
                for tax in taxonomies:
                    if isinstance(tax, dict) and tax.get("primary") == True:
                        found_specialty = tax.get("desc")
                        data_source = "NPI Registry"
                        break
                
                # If no primary found, get first available
                if not found_specialty and taxonomies:
                    for tax in taxonomies:
                        if isinstance(tax, dict):
                            desc = tax.get("desc")
                            if desc:
                                found_specialty = desc
                                data_source = "NPI Registry"
                                break
        
        # If no specialty in NPI, try other sources
        if not found_specialty and scraped_data.get("specialty"):
            found_specialty = scraped_data.get("specialty")
            data_source = "Provider Directories"
        
        # Try services offered from scraped data
        if not found_specialty:
            services_offered = scraped_data.get("services_offered", [])
            if isinstance(services_offered, list) and services_offered:
                found_specialty = services_offered[0]  # Take first service as specialty
                data_source = "Provider Directories"
        
        # Set results
        if found_specialty:
            result["scraped_data_field_a"] = found_specialty
            result["scraped_from"] = data_source
            
            if input_specialty and input_specialty.strip():
                input_lower = input_specialty.lower()
                specialty_lower = found_specialty.lower()
                result["matches"] = input_lower in specialty_lower or specialty_lower in input_lower
            else:
                result["matches"] = None
        
        logger.debug(f"Specialty verification: input='{input_specialty}', found='{found_specialty}', source='{data_source}'")
        
    except Exception as e:
        logger.error(f"Error in verify_specialty: {str(e)}")
    
    return result

def verify_address(input_address: str, scraped_data: Dict, best_provider) -> Dict:
    """Verify address against scraped data"""
    result = {
        "input_field_a": input_address if input_address else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        best_address = None
        best_similarity = 0.0
        data_source = None
        
        # First, try NPI Registry data
        if best_provider and isinstance(best_provider, dict):
            all_addresses = []
            
            # Add addresses from NPI
            addresses = best_provider.get("addresses", [])
            if isinstance(addresses, list):
                all_addresses.extend(addresses)
            
            # Add practiceLocations from NPI  
            practice_locations = best_provider.get("practiceLocations", [])
            if isinstance(practice_locations, list):
                all_addresses.extend(practice_locations)
            
            for addr in all_addresses:
                if isinstance(addr, dict):
                    # Handle both address types
                    addr_line1 = addr.get('address_1', '')
                    addr_line2 = addr.get('address_2', '')
                    city = addr.get('city', '')
                    state = addr.get('state', '')
                    postal = addr.get('postal_code', '')
                    
                    # Format address
                    formatted_address = f"{addr_line1} {addr_line2}".strip()
                    if city or state or postal:
                        formatted_address += f", {city}, {state} {postal}".strip()
                    
                    if formatted_address.strip():
                        if input_address and input_address.strip():
                            similarity = calculate_address_similarity(input_address, formatted_address)
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_address = formatted_address
                                data_source = "NPI Registry"
                        elif not best_address:
                            best_address = formatted_address
                            data_source = "NPI Registry"
        
        # If no address found in NPI, try Google Places
        if not best_address and scraped_data.get("address"):
            google_address = scraped_data.get("address")
            if google_address and google_address.strip():
                best_address = google_address
                data_source = "Google Places"
                
                if input_address and input_address.strip():
                    best_similarity = calculate_address_similarity(input_address, google_address)
        
        # Try other scraped sources if still no address
        if not best_address:
            # Check practice_locations from scraped_data
            practice_locations = scraped_data.get("practice_locations", [])
            if isinstance(practice_locations, list) and practice_locations:
                location = practice_locations[0]  # Take first location
                if isinstance(location, dict) and location.get("address"):
                    best_address = location["address"]
                    data_source = "Provider Directories"
                    
                    if input_address and input_address.strip():
                        best_similarity = calculate_address_similarity(input_address, best_address)
        
        # Set results
        if best_address:
            result["scraped_data_field_a"] = best_address
            result["scraped_from"] = data_source
            
            if input_address and input_address.strip():
                result["matches"] = best_similarity >= 0.6
            else:
                result["matches"] = None
        
        logger.debug(f"Address verification: input='{input_address}', found='{best_address}', source='{data_source}', similarity={best_similarity}")
                    
    except Exception as e:
        logger.error(f"Error in verify_address: {str(e)}")
    
    return result

def verify_phone_number(input_phone: str, scraped_data: Dict, best_provider) -> Dict:
    """Verify phone number against scraped data"""
    result = {
        "input_field_a": input_phone if input_phone else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    # Normalize phone number function
    def normalize_phone(phone):
        if not phone:
            return ""
        return ''.join(filter(str.isdigit, phone))
    
    try:
        found_phone = None
        data_source = None
        
        # First, try NPI Registry
        if best_provider and isinstance(best_provider, dict):
            # Check both addresses and practiceLocations for phone numbers
            all_locations = []
            
            addresses = best_provider.get("addresses", [])
            if isinstance(addresses, list):
                all_locations.extend(addresses)
                
            practice_locations = best_provider.get("practiceLocations", [])
            if isinstance(practice_locations, list):
                all_locations.extend(practice_locations)
            
            for addr in all_locations:
                if (isinstance(addr, dict) and 
                    addr.get("telephone_number")):
                    
                    found_phone = addr.get("telephone_number")
                    data_source = "NPI Registry"
                    break
        
        # If no phone in NPI, try Google Places
        if not found_phone and scraped_data.get("phone_number"):
            found_phone = scraped_data.get("phone_number")
            data_source = "Google Places"
        
        # Try other scraped sources
        if not found_phone:
            practice_locations = scraped_data.get("practice_locations", [])
            if isinstance(practice_locations, list) and practice_locations:
                for location in practice_locations:
                    if isinstance(location, dict) and location.get("phone"):
                        found_phone = location["phone"]
                        data_source = "Provider Directories"
                        break
        
        # Set results
        if found_phone:
            result["scraped_data_field_a"] = found_phone
            result["scraped_from"] = data_source
            
            if input_phone and input_phone.strip():
                result["matches"] = normalize_phone(input_phone) == normalize_phone(found_phone)
            else:
                result["matches"] = None
        
        logger.debug(f"Phone verification: input='{input_phone}', found='{found_phone}', source='{data_source}'")
                    
    except Exception as e:
        logger.error(f"Error in verify_phone_number: {str(e)}")
    
    return result

def verify_license_number(input_license: str, scraped_data: Dict, best_provider, request_specialty: str) -> Dict:
    """Verify license number against scraped data"""
    result = {
        "input_field_a": input_license if input_license else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        if best_provider and isinstance(best_provider, dict):
            taxonomies = best_provider.get("taxonomies", [])
            if isinstance(taxonomies, list):
                matching_license = None
                logger.debug(f"Looking for license matching specialty: '{request_specialty}'")
                logger.debug(f"Available taxonomies: {[{tax.get('desc'): tax.get('license')} for tax in taxonomies if isinstance(tax, dict)]}")
                
                # Strategy 1: Find license where desc matches specialty (case insensitive)
                if request_specialty and request_specialty.strip():
                    for tax in taxonomies:
                        if isinstance(tax, dict) and tax.get("desc") and tax.get("license"):
                            tax_desc = tax.get("desc", "").lower().strip()
                            specialty_lower = request_specialty.lower().strip()
                            
                            # More flexible matching
                            specialty_match = (
                                specialty_lower == tax_desc or
                                specialty_lower in tax_desc or 
                                tax_desc in specialty_lower or
                                # Handle common variations
                                (specialty_lower == "family medicine" and "family" in tax_desc) or
                                (specialty_lower == "internal medicine" and "internal" in tax_desc) or
                                (specialty_lower == "cardiology" and ("cardio" in tax_desc or "heart" in tax_desc))
                            )
                            
                            logger.debug(f"Checking taxonomy: desc='{tax_desc}', license='{tax.get('license')}', specialty_match={specialty_match}")
                            
                            if specialty_match and tax.get("license", "").strip():
                                matching_license = tax.get("license").strip()
                                logger.debug(f"Found matching license by specialty: {matching_license}")
                                break
                
                # Strategy 2: If no specialty match found, fall back to primary license
                if not matching_license:
                    logger.debug("No specialty match found, looking for primary license...")
                    for tax in taxonomies:
                        if isinstance(tax, dict) and tax.get("primary") == True and tax.get("license"):
                            license_value = tax.get("license", "").strip()
                            if license_value and license_value != "--" and license_value.upper() != "N/A":
                                matching_license = license_value
                                logger.debug(f"Found primary license: {matching_license}")
                                break
                
                # Strategy 3: If still no license found, get first available non-empty license
                if not matching_license:
                    logger.debug("No primary license found, using first available license...")
                    for tax in taxonomies:
                        if isinstance(tax, dict) and tax.get("license"):
                            license_value = tax.get("license", "").strip()
                            if license_value and license_value != "--" and license_value.upper() != "N/A":
                                matching_license = license_value
                                logger.debug(f"Found first available license: {matching_license}")
                                break
                
                # Set the result if we found a license
                if matching_license:
                    result["scraped_data_field_a"] = matching_license
                    result["scraped_from"] = "NPI Registry"
                    
                    if input_license and input_license.strip():
                        # Compare licenses (case insensitive, strip whitespace)
                        input_clean = input_license.upper().strip()
                        found_clean = matching_license.upper().strip()
                        result["matches"] = input_clean == found_clean
                        logger.debug(f"License comparison: input='{input_clean}' vs found='{found_clean}' -> matches={result['matches']}")
                    else:
                        result["matches"] = None  # No input to compare against
                        logger.debug(f"No input license provided, but found license: {matching_license}")
                else:
                    logger.debug("No license found in any taxonomy")
                    
    except Exception as e:
        logger.error(f"Error in verify_license_number: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.debug(f"Final license result: {result}")
    return result

def verify_insurance_networks(input_networks: List[str], scraped_data: Dict, best_provider) -> Dict:
    """Verify insurance networks against scraped data"""
    result = {
        "input_field_a": input_networks if input_networks else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        if best_provider and isinstance(best_provider, dict):
            identifiers = best_provider.get("identifiers", [])
            found_networks = []
            
            if isinstance(identifiers, list):
                for identifier in identifiers:
                    if not isinstance(identifier, dict):
                        continue
                        
                    desc = identifier.get("desc", "")
                    issuer = identifier.get("issuer", "")
                    
                    if desc and "MEDICAID" in desc.upper():
                        found_networks.append("Medicaid")
                    elif desc and "MEDICARE" in desc.upper():
                        found_networks.append("Medicare")
                    elif issuer:
                        issuer_lower = issuer.lower()
                        if "blue shield" in issuer_lower or "blue cross" in issuer_lower:
                            found_networks.append("Blue Cross Blue Shield")
                        elif "aetna" in issuer_lower:
                            found_networks.append("Aetna")
                        elif "cigna" in issuer_lower:
                            found_networks.append("Cigna")
                        elif "humana" in issuer_lower:
                            found_networks.append("Humana")
                        elif "united" in issuer_lower:
                            found_networks.append("UnitedHealthcare")
            
            if found_networks:
                unique_networks = list(set(found_networks))
                result["scraped_data_field_a"] = unique_networks
                result["scraped_from"] = "NPI Registry"
                
                if input_networks and len(input_networks) > 0:
                    input_set = set(input_networks)
                    found_set = set(unique_networks)
                    matches = len(input_set & found_set)
                    result["matches"] = matches > 0
                else:
                    result["matches"] = None
                    
    except Exception as e:
        logger.error(f"Error in verify_insurance_networks: {str(e)}")
    
    return result

def verify_services_offered(input_services: str, scraped_data: Dict, best_provider) -> Dict:
    """Verify services offered against scraped data"""
    result = {
        "input_field_a": input_services if input_services else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": None  # Changed from False to None - will be set based on logic
    }
    
    try:
        services_found = scraped_data.get("services_offered", [])
        
        if services_found and isinstance(services_found, list):
            result["scraped_data_field_a"] = services_found
            result["scraped_from"] = "Provider Directories"
            
            if input_services and input_services.strip():
                input_lower = input_services.lower()
                matching_services = []
                
                for service in services_found:
                    if isinstance(service, str):
                        service_lower = service.lower()
                        if (service_lower in input_lower or 
                            any(word in input_lower for word in service_lower.split() if len(word) > 2)):
                            matching_services.append(service)
                
                result["matches"] = len(matching_services) > 0
            else:
                result["matches"] = None
                
    except Exception as e:
        logger.error(f"Error in verify_services_offered: {str(e)}")
    
    return result

# API Endpoints
@router.post(VERIFY_DOCTOR, response_model=VerificationResult)
async def verify_doctor(request: DoctorVerificationRequest, db: Session = Depends(get_db)):
    """
    Verify doctor credentials and information through multiple data sources
    """
    try:
        logger.info(f"Starting doctor verification for: {request.fullName}")
        
        # Generate verification ID
        verification_id = f"VER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.fullName) % 10000:04d}"
          # Search for doctor information
        scraped_data = search_doctor_info(request.fullName, request.specialty)
        
        # Log scraped data for debugging
        logger.debug(f"Scraped data for {request.fullName}: {scraped_data.keys() if scraped_data else 'None'}")
        if scraped_data and scraped_data.get("npi_data"):
            npi_data = scraped_data.get("npi_data", {})
            logger.debug(f"NPI data result count: {npi_data.get('result_count', 0)}")
            
        # Analyze verification results
        verification_result = await analyze_verification(request, scraped_data)
        
        # Create database record
        db_report = DoctorReport(
            verification_id=verification_id,
            full_name_input=verification_result["fullName"]["input_field_a"],
            full_name_scraped=verification_result["fullName"]["scraped_data_field_a"],
            full_name_scraped_from=verification_result["fullName"]["scraped_from"],
            full_name_matches=verification_result["fullName"]["matches"],
            specialty_input=verification_result["specialty"]["input_field_a"],
            specialty_scraped=verification_result["specialty"]["scraped_data_field_a"],
            specialty_scraped_from=verification_result["specialty"]["scraped_from"],
            specialty_matches=verification_result["specialty"]["matches"],
            address_input=verification_result["address"]["input_field_a"],
            address_scraped=verification_result["address"]["scraped_data_field_a"],
            address_scraped_from=verification_result["address"]["scraped_from"],
            address_matches=verification_result["address"]["matches"],
            phone_number_input=verification_result["phoneNumber"]["input_field_a"],
            phone_number_scraped=verification_result["phoneNumber"]["scraped_data_field_a"],
            phone_number_scraped_from=verification_result["phoneNumber"]["scraped_from"],
            phone_number_matches=verification_result["phoneNumber"]["matches"],
            license_number_input=verification_result["licenseNumber"]["input_field_a"],
            license_number_scraped=verification_result["licenseNumber"]["scraped_data_field_a"],
            license_number_scraped_from=verification_result["licenseNumber"]["scraped_from"],
            license_number_matches=verification_result["licenseNumber"]["matches"],
            insurance_networks_input=verification_result["insuranceNetworks"]["input_field_a"],
            insurance_networks_scraped=verification_result["insuranceNetworks"]["scraped_data_field_a"],
            insurance_networks_scraped_from=verification_result["insuranceNetworks"]["scraped_from"],
            insurance_networks_matches=verification_result["insuranceNetworks"]["matches"],
            services_offered_input=verification_result["servicesOffered"]["input_field_a"],
            services_offered_scraped=verification_result["servicesOffered"]["scraped_data_field_a"],
            services_offered_scraped_from=verification_result["servicesOffered"]["scraped_from"],
            services_offered_matches=verification_result["servicesOffered"]["matches"]
        )
        
        # Save to database
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        # Prepare response with simplified structure
        result = VerificationResult(
            verification_id=verification_id,
            timestamp=datetime.now().isoformat(),
            fullName=verification_result["fullName"],
            specialty=verification_result["specialty"],
            address=verification_result["address"],
            phoneNumber=verification_result["phoneNumber"],
            licenseNumber=verification_result["licenseNumber"],
            insuranceNetworks=verification_result["insuranceNetworks"],
            servicesOffered=verification_result["servicesOffered"]
        )
        
        logger.info(f"Verification completed and saved to database for {request.fullName}")
        return result
        
    except Exception as e:
        logger.error(f"Error in doctor verification: {str(e)}")
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@router.post(SEARCH_DOCTOR, response_model=SearchResult)
async def search_doctor(request: DoctorSearchRequest):
    """
    Search for doctor information without verification
    """
    try:
        logger.info(f"Starting doctor search for: {request.name}")
        
        # Generate search ID
        search_id = f"SEARCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.name) % 10000:04d}"
        
        # Search for doctor information
        search_results = search_doctor_info(request.name, request.specialty or "")
        
        # Format results
        formatted_results = []
        if search_results.get("npi_data", {}).get("providers"):
            for provider in search_results["npi_data"]["providers"]:
                formatted_results.append({
                    "npi": provider.get("npi"),
                    "name": provider.get("name"),
                    "specialty": provider.get("taxonomies", []),
                    "locations": provider.get("practice_locations", []),
                    "credentials": provider.get("credential"),
                    "source": "NPI Registry"
                })
        
        # Add Google Places data if available
        if search_results.get("google_rating"):
            formatted_results.append({
                "name": request.name,
                "address": search_results.get("address"),
                "phone": search_results.get("phone_number"),
                "rating": search_results.get("google_rating"),
                "reviews": len(search_results.get("google_reviews", [])),
                "source": "Google Places"
            })
        
        result = SearchResult(
            search_id=search_id,
            timestamp=datetime.now().isoformat(),
            query=request.dict(),
            results=formatted_results,
            total_found=len(formatted_results),
            sources_used=search_results.get("scraped_sources", [])
        )
        
        logger.info(f"Search completed for {request.name}: {len(formatted_results)} results found")
        return result
        
    except Exception as e:
        logger.error(f"Error in doctor search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get(GET_SPECIALTIES)
async def get_specialties():
    """Get list of available medical specialties"""
    return {"specialties": SPECIALTIES}

@router.get(GET_INSURANCE_NETWORKS)
async def get_insurance_networks():
    """Get list of available insurance networks"""
    return {"networks": INSURANCE_NETWORKS}

def validate_pdf_content(provider_info: Dict[str, str]) -> List[str]:
    """Validate extracted PDF content and return list of validation errors"""
    errors = []
    
    # Check if we have minimum required information
    if not provider_info.get("fullName") or len(provider_info.get("fullName", "").strip()) < 3:
        errors.append("No valid doctor name found in PDF")
    
    if not provider_info.get("specialty") or len(provider_info.get("specialty", "").strip()) < 2:
        errors.append("No valid medical specialty found in PDF")
    
    # Check if name looks like a real name (at least first and last name)
    full_name = provider_info.get("fullName", "")
    if full_name and len(full_name.strip().split()) < 2:
        errors.append("Doctor name must include both first and last name")
    
    # Check if specialty matches our known specialties
    specialty = provider_info.get("specialty", "")
    if specialty:
        specialty_valid = any(known_spec.lower() in specialty.lower() or specialty.lower() in known_spec.lower() 
                            for known_spec in SPECIALTIES)
        if not specialty_valid:
            errors.append(f"Specialty '{specialty}' is not recognized as a valid medical specialty")
    
    return errors

@router.post(EXTRACT_PDF)
async def extract_provider_from_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Extract provider information from uploaded PDF and perform verification"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        file_content = await file.read()
        
        # Extract text from PDF
        extracted_text = await extract_text_from_pdf(file_content)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")
        
        # Parse provider information
        provider_info = parse_provider_info(extracted_text)
        
        # Validate that we extracted meaningful information
        validation_errors = validate_pdf_content(provider_info)
        if validation_errors:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": "PDF validation failed",
                    "message": "The uploaded PDF does not contain valid doctor information",
                    "details": validation_errors,
                    "extracted_info": provider_info
                }
            )
        
        # Create verification request from extracted data
        verification_request = DoctorVerificationRequest(
            fullName=provider_info.get("fullName", ""),
            specialty=provider_info.get("specialty", ""),
            address=provider_info.get("address"),
            phoneNumber=provider_info.get("phoneNumber"),
            licenseNumber=provider_info.get("licenseNumber"),
            insuranceNetworks=[],  # Not extracted from PDF
            servicesOffered=provider_info.get("servicesOffered")
        )
        
        # Perform verification if we have minimum required data
        verification_results = None
        db_report = None
        
        if verification_request.fullName and verification_request.specialty:
            try:
                # Generate verification ID
                verification_id = f"VER_PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(verification_request.fullName) % 10000:04d}"
                
                # Search for doctor information
                scraped_data = search_doctor_info(
                    verification_request.fullName,
                    verification_request.specialty
                )
                
                # Analyze verification results
                verification_result = await analyze_verification(verification_request, scraped_data)
                
                # Create database record
                db_report = DoctorReport(
                    verification_id=verification_id,
                    full_name_input=verification_result["fullName"]["input_field_a"],
                    full_name_scraped=verification_result["fullName"]["scraped_data_field_a"],
                    full_name_scraped_from=verification_result["fullName"]["scraped_from"],
                    full_name_matches=verification_result["fullName"]["matches"],
                    specialty_input=verification_result["specialty"]["input_field_a"],
                    specialty_scraped=verification_result["specialty"]["scraped_data_field_a"],
                    specialty_scraped_from=verification_result["specialty"]["scraped_from"],
                    specialty_matches=verification_result["specialty"]["matches"],
                    address_input=verification_result["address"]["input_field_a"],
                    address_scraped=verification_result["address"]["scraped_data_field_a"],
                    address_scraped_from=verification_result["address"]["scraped_from"],
                    address_matches=verification_result["address"]["matches"],
                    phone_number_input=verification_result["phoneNumber"]["input_field_a"],
                    phone_number_scraped=verification_result["phoneNumber"]["scraped_data_field_a"],
                    phone_number_scraped_from=verification_result["phoneNumber"]["scraped_from"],
                    phone_number_matches=verification_result["phoneNumber"]["matches"],
                    license_number_input=verification_result["licenseNumber"]["input_field_a"],
                    license_number_scraped=verification_result["licenseNumber"]["scraped_data_field_a"],
                    license_number_scraped_from=verification_result["licenseNumber"]["scraped_from"],
                    license_number_matches=verification_result["licenseNumber"]["matches"],
                    insurance_networks_input=verification_result["insuranceNetworks"]["input_field_a"],
                    insurance_networks_scraped=verification_result["insuranceNetworks"]["scraped_data_field_a"],
                    insurance_networks_scraped_from=verification_result["insuranceNetworks"]["scraped_from"],
                    insurance_networks_matches=verification_result["insuranceNetworks"]["matches"],
                    services_offered_input=verification_result["servicesOffered"]["input_field_a"],
                    services_offered_scraped=verification_result["servicesOffered"]["scraped_data_field_a"],
                    services_offered_scraped_from=verification_result["servicesOffered"]["scraped_from"],
                    services_offered_matches=verification_result["servicesOffered"]["matches"]
                )
                
                # Save to database
                db.add(db_report)
                db.commit()
                db.refresh(db_report)
                
                # Create the same result structure as the verify endpoint
                verification_results = VerificationResult(
                    verification_id=verification_id,
                    timestamp=datetime.now().isoformat(),
                    fullName=verification_result["fullName"],
                    specialty=verification_result["specialty"],
                    address=verification_result["address"],
                    phoneNumber=verification_result["phoneNumber"],
                    licenseNumber=verification_result["licenseNumber"],
                    insuranceNetworks=verification_result["insuranceNetworks"],
                    servicesOffered=verification_result["servicesOffered"]
                )
                
                logger.info(f"PDF verification completed and saved to database for {verification_request.fullName}")
                
            except Exception as e:
                logger.error(f"Verification failed for PDF data: {str(e)}")
                if db:
                    db.rollback()
                # Continue without verification results
        
        return {
            "success": True,
            "extracted_text": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            "provider_info": provider_info,
            "verification_results": verification_results,
            "filename": file.filename,
            "timestamp": datetime.now().isoformat(),
            "has_verification": verification_results is not None,
            "saved_to_database": db_report is not None,
            "report_id": str(db_report.report_id) if db_report else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        if db:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

async def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file content"""
    full_text = ""
    
    try:
        # Validate file size first
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="PDF file is empty")
        
        # Try with pdfplumber first (better for complex layouts)
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            if len(pdf.pages) == 0:
                raise HTTPException(status_code=400, detail="PDF contains no pages")
                
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        full_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}, trying PyPDF2")
        
        # Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            
            if len(pdf_reader.pages) == 0:
                raise HTTPException(status_code=400, detail="PDF contains no pages")
                
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        full_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
                    
        except HTTPException:
            raise
        except Exception as e2:
            logger.error(f"Both pdfplumber and PyPDF2 failed: {e2}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "PDF processing failed",
                    "message": "Could not extract text from PDF. The PDF may be corrupted, password-protected, or contain only images."
                }
            )
    
    return full_text.strip()

def parse_provider_info(text: str) -> Dict[str, str]:
    """Parse provider information from extracted PDF text with intelligent field detection"""
    provider_info = {
        "fullName": "",
        "specialty": "",
        "address": "",
        "phoneNumber": "",
        "licenseNumber": "",
        "servicesOffered": ""
    }
    
    # Normalize text for better parsing
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    lines = text.split('\n')
    
    # Smart field detection - look for key-value patterns
    field_patterns = {
        'fullName': [
            r'(?:name|full\s*name|fullname|provider\s*name|doctor\s*name|physician\s*name|dr\s*name)\s*[:\-\s]\s*([a-zA-Z\s\.,]+?)(?:\n|$|,\s*M\.?D\.?)',
            r'(?:name|full\s*name|fullname)\s*[:\-\s]\s*([a-zA-Z\s\.,]+?)(?:\s+specialty|\s+phone|\s+address|\n|$)',
            r'(?:^|\n)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,?\s*M\.?D\.?|\s*$)',
            r'(?:Dr\.?\s+)([A-Z][a-z]+\s+[A-Z][a-z]+)',
            # More flexible pattern for simple "Name : Value" format
            r'name\s*:\s*([a-zA-Z\s]+?)(?:\s*\n|\s*specialty|\s*address|\s*phone|$)',
        ],
        'specialty': [
            r'(?:specialty|speciality|specialization|field|practice\s*area|medical\s*specialty)\s*[:\-\s]\s*([a-zA-Z\s&,\-()]+?)(?:\n|$)',
            # Direct specialty matching from our list
        ],
        'address': [
            r'(?:address|location|clinic\s*address|office\s*address|practice\s*address)\s*[:\-\s]\s*([a-zA-Z0-9\s,.\-]+?)(?=\s*(?:phone|tel|telephone|contact|cell|mobile|specialty|license|name|$|\n))',
            r'([a-zA-Z\s,]+,\s*[a-zA-Z\s]+(?:,\s*[a-zA-Z]{2})?)(?:\s*\d{5,6})?(?=\s*(?:phone|tel|telephone|contact|cell|mobile|specialty|license|name|$|\n))',  # City, State pattern
            r'(\d+\s+[a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)(?:\s+[a-zA-Z0-9\s,]+?)?)(?=\s*(?:phone|tel|telephone|contact|cell|mobile|specialty|license|name|$|\n))',
        ],
        'phoneNumber': [
            r'(?:phone|tel|telephone|contact|cell|mobile|number|ph|call)\s*[:\-\s]?\s*(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            r'(\d{10})',  # Simple 10-digit number
        ],
        'licenseNumber': [
            r'(?:license|medical\s*license|state\s*license|license\s*number|license\s*no|lic|reg\s*no|registration)\s*[:\-\s#]?\s*([A-Z0-9]+)',
            r'(?:license|lic)\.?\s*#?\s*([A-Z0-9]{4,})',
        ]
    }
    
    # Extract full name with intelligent patterns
    for pattern in field_patterns['fullName']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Clean up common suffixes and prefixes
            name = re.sub(r'^(Dr\.?|Doctor)\s*', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s*,?\s*(M\.?D\.?|MD|Ph\.?D\.?|PhD).*$', '', name, flags=re.IGNORECASE)
            # Validate it looks like a name (at least 2 words, proper capitalization)
            if len(name.split()) >= 2 and not name.isupper() and not name.islower():
                provider_info["fullName"] = name.title()
                break
    
    # Extract specialty - try pattern matching first, then direct specialty matching
    for pattern in field_patterns['specialty']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            specialty_text = match.group(1).strip()
            # Check if extracted text matches any of our specialties
            for specialty in SPECIALTIES:
                if specialty.lower() in specialty_text.lower():
                    provider_info["specialty"] = specialty
                    break
            if provider_info["specialty"]:
                break
    
    # If no specialty found through patterns, try direct matching
    if not provider_info["specialty"]:
        for specialty in SPECIALTIES:
            if re.search(r'\b' + re.escape(specialty.lower()) + r'\b', text.lower()):
                provider_info["specialty"] = specialty
                break
    
    # Extract address with multiple approaches
    for pattern in field_patterns['address']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            address = match.group(1).strip()
            # Clean up and validate address
            address = re.sub(r'^[:\-\s]+', '', address)  # Remove leading separators
            address = re.sub(r'[:\-\s]+$', '', address)  # Remove trailing separators
            # Basic validation - should have at least city/state or street info
            if (len(address.split()) >= 2 and 
                (any(word.lower() in address.lower() for word in ['street', 'st', 'avenue', 'ave', 'road', 'rd', 'drive', 'dr', 'lane', 'ln']) or
                 ',' in address)):  # Contains comma (likely city, state)
                provider_info["address"] = address
                break
    
    # Extract phone number with flexible formatting
    for pattern in field_patterns['phoneNumber']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            phone = match.group(1).strip()
            # Clean and format phone number
            phone_digits = re.sub(r'[^\d]', '', phone)
            if len(phone_digits) == 10:
                # Format as (XXX) XXX-XXXX
                provider_info["phoneNumber"] = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
                break
            elif len(phone_digits) == 11 and phone_digits[0] == '1':
                # Remove leading 1 and format
                phone_digits = phone_digits[1:]
                provider_info["phoneNumber"] = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
                break
    
    # Extract license number
    for pattern in field_patterns['licenseNumber']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            license_num = match.group(1).strip()
            # Basic validation - should be alphanumeric and reasonable length
            if re.match(r'^[A-Z0-9]{4,20}$', license_num, re.IGNORECASE):
                provider_info["licenseNumber"] = license_num.upper()
                break
    
    # Extract services with enhanced keyword detection
    service_keywords = [
        'consultation', 'diagnosis', 'treatment', 'surgery', 'examination',
        'therapy', 'screening', 'preventive care', 'emergency care',
        'specialist care', 'follow-up', 'procedure', 'immunization',
        'checkup', 'physical exam', 'wellness', 'chronic disease management',
        'telemedicine', 'urgent care', 'routine care', 'medical evaluation'
    ]
    
    # Look for services in context
    services_pattern = r'(?:services|treatments|procedures|specialties|offers|provides)\s*[:\-\s]\s*([^.\n]+)'
    services_match = re.search(services_pattern, text, re.IGNORECASE | re.MULTILINE)
    
    found_services = set()
    
    if services_match:
        services_text = services_match.group(1).lower()
        for keyword in service_keywords:
            if keyword in services_text:
                found_services.add(keyword.title())
    else:
        # Fallback to general keyword search
        for keyword in service_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text.lower()):
                found_services.add(keyword.title())
    
    if found_services:
        provider_info["servicesOffered"] = ", ".join(sorted(list(found_services))[:5])
    
    return provider_info

@router.get(HEALTH_CHECK)
async def health_check():
    """Health check for doctor verification service"""
    try:
        # Test NPI API connectivity
        scraper = DoctorInfoScraper()
        test_result = scraper._search_npi_registry("Test", "Internal Medicine")
        
        return {
            "status": "healthy",
            "services": {
                "npi_registry": "operational" if test_result else "limited",
                "web_scraping": "operational",
                "google_places": "operational" if os.getenv('GOOGLE_PLACES_API_KEY') else "disabled"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get(GET_REPORTS, response_model=GetReportsResponse)
async def get_reports(
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(10, description="Maximum number of records to return"),
    full_name: Optional[str] = Query(None, description="Filter by doctor's full name (partial match)"),
    specialty: Optional[str] = Query(None, description="Filter by medical specialty (partial match)"),
    sort_field: Optional[str] = Query("created_at", description="Field to sort by (created_at, full_name, specialty, verification_id, etc.)"),
    sort_order: Optional[str] = Query("descend", description="Sort order (ascend/descend)"),
    db: Session = Depends(get_db)
):
    """
    Get all doctor reports with advanced filtering and pagination
    
    Supports filtering by:
    - full_name: partial match on doctor's name (input or scraped)
    - specialty: partial match on specialty (input or scraped)  

    Supports sorting by:
    - sort_field: full_name, specialty
    - sort_order: ascend/descend
    """
    try:
        logger.info(f"Fetching reports with filters - full_name: {full_name}, specialty: {specialty}")
        
        # Validate pagination parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        # Build base query
        query = db.query(DoctorReport)
        
        # Apply filters
        if full_name and full_name.strip():
            name_filter = full_name.strip()
            query = query.filter(
                or_(
                    func.lower(DoctorReport.full_name_input).contains(func.lower(name_filter)),
                    func.lower(DoctorReport.full_name_scraped).contains(func.lower(name_filter))
                )
            )
        
        if specialty and specialty.strip():
            specialty_filter = specialty.strip()
            query = query.filter(
                or_(
                    func.lower(DoctorReport.specialty_input).contains(func.lower(specialty_filter)),
                    func.lower(DoctorReport.specialty_scraped).contains(func.lower(specialty_filter))
                )
            )
        
        # Get total count for pagination info
        total_count = query.count()
        
        # Apply sorting
        sort_field_map = {
            "full_name": func.coalesce(DoctorReport.full_name_input, DoctorReport.full_name_scraped, ''),
            "specialty": func.coalesce(DoctorReport.specialty_input, DoctorReport.specialty_scraped, '')
        }
        
        # Default to created_at if sort_field is not specified or not found in map
        sort_column = sort_field_map.get(sort_field, DoctorReport.created_at)
        
        if sort_order and sort_order.lower() == "ascend":
            sort_expr = sort_column.asc()
        else:
            sort_expr = sort_column.desc()
        
        # Apply pagination and get results
        reports = query.order_by(sort_expr).offset(skip).limit(limit).all()
        
        # Convert to response format
        report_responses = []
        for report in reports:
            report_response = DoctorReportResponse(
                report_id=str(report.report_id),
                verification_id=report.verification_id,
                full_name_input=report.full_name_input,
                full_name_scraped=report.full_name_scraped,
                full_name_scraped_from=report.full_name_scraped_from,
                full_name_matches=report.full_name_matches,
                specialty_input=report.specialty_input,
                specialty_scraped=report.specialty_scraped,
                specialty_scraped_from=report.specialty_scraped_from,
                specialty_matches=report.specialty_matches,
                address_input=report.address_input,
                address_scraped=report.address_scraped,
                address_scraped_from=report.address_scraped_from,
                address_matches=report.address_matches,
                phone_number_input=report.phone_number_input,
                phone_number_scraped=report.phone_number_scraped,
                phone_number_scraped_from=report.phone_number_scraped_from,
                phone_number_matches=report.phone_number_matches,
                license_number_input=report.license_number_input,
                license_number_scraped=report.license_number_scraped,
                license_number_scraped_from=report.license_number_scraped_from,
                license_number_matches=report.license_number_matches,
                insurance_networks_input=report.insurance_networks_input,
                insurance_networks_scraped=report.insurance_networks_scraped,
                insurance_networks_scraped_from=report.insurance_networks_scraped_from,
                insurance_networks_matches=report.insurance_networks_matches,
                services_offered_input=report.services_offered_input,
                services_offered_scraped=report.services_offered_scraped,
                services_offered_scraped_from=report.services_offered_scraped_from,
                services_offered_matches=report.services_offered_matches,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat()
            )
            report_responses.append(report_response)
        
        # Prepare response
        response = GetReportsResponse(
            reports=report_responses,
            total_count=total_count,
            skip=skip,
            limit=limit,
            has_next=skip + limit < total_count,
            has_previous=skip > 0
        )
        
        logger.info(f"Retrieved {len(report_responses)} reports out of {total_count} total")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")

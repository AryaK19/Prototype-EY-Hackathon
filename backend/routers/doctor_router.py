from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import logging
import sys
import os
from datetime import datetime
import json

# Add helpers to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'helpers'))
from funtion import search_doctor_info, DoctorInfoScraper

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
        "matches": False
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
        "matches": False
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
        "matches": False
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
        "matches": False
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
        "matches": False
    }
    
    try:
        if best_provider and isinstance(best_provider, dict):
            taxonomies = best_provider.get("taxonomies", [])
            if isinstance(taxonomies, list):
                # First, find license where desc matches specialty
                matching_license = None
                logger.debug(f"Looking for license matching specialty: {request_specialty}")
                
                for tax in taxonomies:
                    if isinstance(tax, dict) and tax.get("desc") and tax.get("license"):
                        tax_desc = tax.get("desc", "").lower()
                        specialty_match = request_specialty.lower() in tax_desc or tax_desc in request_specialty.lower()
                        
                        logger.debug(f"Checking taxonomy: desc='{tax_desc}', license='{tax.get('license')}', specialty_match={specialty_match}")
                        
                        if specialty_match:
                            matching_license = tax.get("license")
                            logger.debug(f"Found matching license: {matching_license}")
                            break
                
                # If no specialty match found, fall back to primary license
                if not matching_license:
                    for tax in taxonomies:
                        if isinstance(tax, dict) and tax.get("primary") == True and tax.get("license"):
                            matching_license = tax.get("license")
                            logger.debug(f"Using primary license: {matching_license}")
                            break
                
                # If still no license found, get first available
                if not matching_license:
                    for tax in taxonomies:
                        if isinstance(tax, dict) and tax.get("license"):
                            matching_license = tax.get("license")
                            logger.debug(f"Using first available license: {matching_license}")
                            break
                
                if matching_license and matching_license.strip():
                    result["scraped_data_field_a"] = matching_license
                    result["scraped_from"] = "NPI Registry"
                    
                    if input_license and input_license.strip():
                        result["matches"] = input_license.upper().strip() == matching_license.upper().strip()
                    else:
                        result["matches"] = None
    except Exception as e:
        logger.error(f"Error in verify_license_number: {str(e)}")
    
    return result

def verify_insurance_networks(input_networks: List[str], scraped_data: Dict, best_provider) -> Dict:
    """Verify insurance networks against scraped data"""
    result = {
        "input_field_a": input_networks if input_networks else None,
        "scraped_data_field_a": None,
        "scraped_from": None,
        "matches": False
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
        "matches": False
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

# Pydantic models for request/response validation
class DoctorVerificationRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=100, description="Doctor's full name")
    specialty: str = Field(..., min_length=2, max_length=50, description="Medical specialty")
    address: Optional[str] = Field(None, max_length=200, description="Practice address")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    licenseNumber: Optional[str] = Field(None, max_length=50, description="Medical license number")
    insuranceNetworks: Optional[List[str]] = Field(default=None, description="Affiliated insurance networks")
    servicesOffered: Optional[str] = Field(None, max_length=500, description="Services offered")

    @validator('phoneNumber')
    def validate_phone(cls, v):
        if v and not v.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').replace('+', '').isdigit():
            raise ValueError('Invalid phone number format')
        return v

    @validator('fullName')
    def validate_name(cls, v):
        if len(v.strip().split()) < 2:
            raise ValueError('Full name must contain at least first and last name')
        return v.strip()

class DoctorSearchRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Doctor's name to search")
    specialty: Optional[str] = Field(None, max_length=50, description="Medical specialty filter")

class FieldVerification(BaseModel):
    input_field_a: Optional[Any] = None
    scraped_data_field_a: Optional[Any] = None
    scraped_from: Optional[str] = None
    matches: Optional[bool] = None

class VerificationResult(BaseModel):
    verification_id: str
    timestamp: str
    fullName: FieldVerification
    specialty: FieldVerification
    address: FieldVerification
    phoneNumber: FieldVerification
    licenseNumber: FieldVerification
    insuranceNetworks: FieldVerification
    servicesOffered: FieldVerification

class SearchResult(BaseModel):
    search_id: str
    timestamp: str
    query: Dict[str, Any]
    results: List[Dict[str, Any]]
    total_found: int
    sources_used: List[str]

# API Endpoints
@router.post("/verify", response_model=VerificationResult)
async def verify_doctor(request: DoctorVerificationRequest):
    """
    Verify doctor credentials and information through multiple data sources
    """
    try:
        logger.info(f"Starting doctor verification for: {request.fullName}")
        
        # Generate verification ID
        verification_id = f"VER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(request.fullName) % 10000:04d}"
        
        # Search for doctor information
        scraped_data = search_doctor_info(request.fullName, request.specialty)
          # Analyze verification results
        verification_result = await analyze_verification(request, scraped_data)
        
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
        
        logger.info(f"Verification completed for {request.fullName}")
        return result
        
    except Exception as e:
        logger.error(f"Error in doctor verification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@router.post("/search", response_model=SearchResult)
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

@router.get("/specialties")
async def get_specialties():
    """Get list of available medical specialties"""
    return {"specialties": SPECIALTIES}

@router.get("/insurance-networks")
async def get_insurance_networks():
    """Get list of available insurance networks"""
    return {"networks": INSURANCE_NETWORKS}

@router.get("/health")
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

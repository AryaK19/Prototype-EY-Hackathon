import requests
import json
import logging
from typing import Dict, List, Optional
import re
from bs4 import BeautifulSoup
import time
from urllib.parse import quote, urljoin
import os
from dotenv import load_dotenv
import traceback
import asyncio
import platform
import sys
import subprocess
import concurrent.futures

# Try to import Playwright, but don't fail if it's not available
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    PlaywrightTimeoutError = Exception

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DoctorInfoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    def get_doctor_details(self, name: str, specialty: str, address: str = None) -> Dict:
        """
        Main function to get comprehensive doctor details from multiple sources
        
        Args:
            name (str): Doctor's full name
            specialty (str): Doctor's specialty/specialization
            address (str, optional): Doctor's address for better WebMD searching
            
        Returns:
            Dict: Comprehensive doctor information
        """
        logger.info(f"Starting search for Dr. {name} - Specialty: {specialty}")
        
        doctor_info = {
            "name": name,
            "specialty": specialty,
            "address": None,
            "phone_number": None,
            "license_number": None,
            "affiliated_insurance_networks": [],
            "services_offered": [],
            "npi_data": {},
            "practice_locations": [],
            "credentials": [],
            "scraped_sources": []
        }        # Step 1: Search NPI Registry
        logger.info("Step 1: Searching NPI Registry...")
        npi_data = self._search_npi_registry(name, specialty)
        if npi_data:
            doctor_info["npi_data"] = npi_data
            doctor_info["scraped_sources"].append("NPI Registry")
            result_count = npi_data.get("result_count", 0)
            logger.info(f"NPI Registry data found: {result_count} records")
        
        # Step 2: Conditionally search Google Places only if NPI didn't provide a good address
        npi_has_address = bool(npi_data and npi_data.get("best_address"))
        
        if npi_has_address:
            logger.info("Step 2: Skipping Google Places (NPI provided address)")
            google_data = {}
            # Use NPI address as best address
            best_address = npi_data.get("best_address")
        else:
            logger.info("Step 2: Searching Google Places for address information...")
            google_data = self._search_google_places(name, specialty)
            if google_data:
                doctor_info.update(google_data)
                doctor_info["scraped_sources"].append("Google Places")
            
            # Step 3: Extract address for WebMD state detection
            # Prioritize provided address, then Google Places, then NPI
            best_address = address
            if not best_address and google_data.get("address"):
                best_address = google_data["address"]
            elif not best_address and npi_data:
                # Try to get address from NPI data
                results = npi_data.get("results", [])
                if results:
                    addresses = results[0].get("addresses", [])
                    for addr in addresses:
                        if addr.get("address_purpose") == "LOCATION":
                            addr_parts = []
                            if addr.get("address_1"):
                                addr_parts.append(addr["address_1"])
                            if addr.get("city"):
                                addr_parts.append(addr["city"])
                            if addr.get("state"):
                                addr_parts.append(addr["state"])
                            best_address = ", ".join(addr_parts)
                            break
        logger.info(f"Best address found for WebMD: {best_address}")
        
        # Step 3: Search Healthgrades (optional)
        logger.info("Step 3: Searching Healthgrades...")
        healthgrades_data = self._search_healthgrades(name, specialty)
        if healthgrades_data:
            # Only update if we don't have the data already
            if healthgrades_data.get("phone_number") and not doctor_info.get("phone_number"):
                doctor_info["phone_number"] = healthgrades_data["phone_number"]
            if healthgrades_data.get("address") and not doctor_info.get("address"):
                doctor_info["address"] = healthgrades_data["address"]
            if healthgrades_data.get("services_offered"):
                doctor_info["services_offered"].extend(healthgrades_data["services_offered"])
            doctor_info["scraped_sources"].append("Healthgrades")
        
        # Step 4: Search WebMD for comprehensive insurance verification (LAST and MOST IMPORTANT)
        logger.info("Step 4: Searching WebMD for insurance verification...")
        webmd_data = self._search_webmd(name, specialty, best_address)
        if webmd_data:
            # Merge WebMD data, prioritizing insurance information
            if webmd_data.get("affiliated_insurance_networks"):
                doctor_info["affiliated_insurance_networks"].extend(webmd_data["affiliated_insurance_networks"])
                # Remove duplicates
                doctor_info["affiliated_insurance_networks"] = list(set(doctor_info["affiliated_insurance_networks"]))
            if webmd_data.get("services_offered"):
                doctor_info["services_offered"].extend(webmd_data["services_offered"])
            if webmd_data.get("phone_number") and not doctor_info.get("phone_number"):
                doctor_info["phone_number"] = webmd_data["phone_number"]
            if webmd_data.get("address") and not doctor_info.get("address"):
                doctor_info["address"] = webmd_data["address"]
            doctor_info["scraped_sources"].append("WebMD")
            
        # Step 5: Search State Medical Board (generic approach)
        logger.info("Step 5: Searching State Medical Board information...")
        license_data = self._search_medical_board(name, specialty)
        if license_data:
            doctor_info.update(license_data)
            doctor_info["scraped_sources"].append("Medical Board")
            
        logger.info(f"Search completed. Found data from {len(doctor_info['scraped_sources'])} sources")
        return doctor_info
    
    def _search_npi_registry(self, name: str, specialty: str) -> Dict:
        """
        Search the NPI Registry using CMS API
        Prioritizes results with identifiers (insurance networks)
        """
        try:
            # NPI Registry API endpoint
            base_url = "https://npiregistry.cms.hhs.gov/api/"
            
            # Parse name (assuming format: "First Last" or "Last, First")
            if "," in name:
                last_name, first_name = [n.strip() for n in name.split(",", 1)]
            else:
                parts = name.strip().split()
                first_name = parts[0] if parts else ""
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            params = {
                "version": "2.1",
                "first_name": first_name,
                "last_name": last_name,
                "taxonomy_description": specialty,
                "limit": 10
            }
            
            logger.info(f"Searching NPI for: {first_name} {last_name}")
            response = self.session.get(base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    logger.warning("No NPI results found")
                    return {}
                
                logger.info(f"Found {len(results)} NPI results")
                
                # Sort results: prioritize those with identifiers
                results_with_identifiers = [r for r in results if r.get("identifiers")]
                results_without_identifiers = [r for r in results if not r.get("identifiers")]
                
                if results_with_identifiers:
                    logger.info(f"✅ Found {len(results_with_identifiers)} results WITH identifiers (insurance networks)")
                    # Use the first result with identifiers
                    selected_result = results_with_identifiers[0]
                    logger.info(f"Selected result with {len(selected_result.get('identifiers', []))} identifiers")
                else:
                    logger.info(f"⚠️ No results with identifiers found, using best name match")
                    # Use name matching to find the best result
                    selected_result = self._find_best_npi_match(results, first_name, last_name)
                
                # Log selected provider details
                selected_name = f"{selected_result.get('basic', {}).get('first_name', '')} {selected_result.get('basic', {}).get('last_name', '')}"
                selected_npi = selected_result.get('number')
                logger.info(f"📋 Selected NPI Result: {selected_name} (NPI: {selected_npi})")
                
                # Extract best address (prioritize LOCATION, then MAILING)
                best_address = self._extract_best_address_from_npi(selected_result)
                if best_address:
                    logger.info(f"📍 Extracted address: {best_address}")
                
                # Reorder results to put selected one first
                reordered_results = [selected_result] + [r for r in results if r != selected_result]
                data["results"] = reordered_results
                
                # Add extracted address to response for easy access
                data["best_address"] = best_address
                data["selected_npi"] = selected_npi
                
                return data
                
        except requests.RequestException as e:
            logger.error(f"NPI Registry search failed: {str(e)}")
        except Exception as e:
            logger.error(f"NPI Registry processing error: {str(e)}")
        return {}
    
    def _find_best_npi_match(self, results: List[Dict], first_name: str, last_name: str) -> Dict:
        """Find the best matching NPI result based on name similarity"""
        target_name = f"{first_name} {last_name}".lower().strip()
        
        best_match = results[0]  # Default to first result
        best_score = 0
        
        for result in results:
            basic = result.get("basic", {})
            result_first = basic.get("first_name", "").lower().strip()
            result_last = basic.get("last_name", "").lower().strip()
            result_name = f"{result_first} {result_last}"
            
            # Calculate simple similarity score
            score = 0
            if first_name.lower() in result_first:
                score += 2
            if last_name.lower() in result_last:
                score += 2
            if result_first in first_name.lower():
                score += 1
            if result_last in last_name.lower():
                score += 1
            
            # Check for exact matches
            if result_first == first_name.lower():
                score += 3
            if result_last == last_name.lower():
                score += 3
            
            if score > best_score:
                best_score = score
                best_match = result
        
        return best_match
    
    def _extract_best_address_from_npi(self, npi_result: Dict) -> Optional[str]:
        """Extract the best address from NPI result (prioritize LOCATION over MAILING)"""
        addresses = npi_result.get("addresses", [])
        
        if not addresses:
            return None
        
        # Look for LOCATION address first
        for addr in addresses:
            if addr.get("address_purpose") == "LOCATION":
                return self._format_npi_address(addr)
        
        # Fall back to MAILING address
        for addr in addresses:
            if addr.get("address_purpose") == "MAILING":
                return self._format_npi_address(addr)
        
        # If no specific type found, use first address
        return self._format_npi_address(addresses[0])
    
    def _format_npi_address(self, addr: Dict) -> str:
        """Format NPI address into a single string"""
        parts = []
        
        if addr.get("address_1"):
            parts.append(addr["address_1"])
        if addr.get("address_2"):
            parts.append(addr["address_2"])
        if addr.get("city"):
            parts.append(addr["city"])
        if addr.get("state"):
            parts.append(addr["state"])
        if addr.get("postal_code"):
            # Clean postal code (remove extra digits)
            postal = addr["postal_code"]
            if len(postal) > 5:
                postal = postal[:5]
            parts.append(postal)
        
        return ", ".join(parts)
    
    def _search_provider_directories(self, name: str, specialty: str, address: str = None) -> Dict:
        """
        Search common healthcare provider directories
        """
        provider_info = {
            "address": None,
            "phone_number": None,
            "services_offered": [],
            "affiliated_insurance_networks": []
        }
        
        try:
            # Search Healthgrades (optional - can be removed)
            healthgrades_data = self._search_healthgrades(name, specialty)
            if healthgrades_data:
                provider_info.update(healthgrades_data)
                
            # Search WebMD (essential for insurance verification)
            webmd_data = self._search_webmd(name, specialty, address)
            if webmd_data:
                # Merge data
                if webmd_data.get("services_offered"):
                    provider_info["services_offered"].extend(webmd_data["services_offered"])
                if webmd_data.get("phone_number") and not provider_info["phone_number"]:
                    provider_info["phone_number"] = webmd_data["phone_number"]
                if webmd_data.get("affiliated_insurance_networks"):
                    provider_info["affiliated_insurance_networks"].extend(webmd_data["affiliated_insurance_networks"])
                if webmd_data.get("address") and not provider_info["address"]:
                    provider_info["address"] = webmd_data["address"]
                    
        except Exception as e:
            logger.error(f"Provider directory search error: {str(e)}")
            
        return provider_info
    
    def _search_healthgrades(self, name: str, specialty: str) -> Dict:
        """
        Search Healthgrades for doctor information
        """
        try:
            search_url = f"https://www.healthgrades.com/usearch?what={quote(name + ' ' + specialty)}&where="
            logger.info(f"Searching Healthgrades: {search_url}")
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for provider cards or listings
                provider_cards = soup.find_all(['div', 'article'], class_=re.compile(r'provider|doctor|listing'))
                
                if provider_cards:
                    # Extract information from first matching result
                    card = provider_cards[0]
                    
                    # Try to extract phone number
                    phone_elements = card.find_all(text=re.compile(r'\(\d{3}\)\s*\d{3}-\d{4}'))
                    phone = phone_elements[0] if phone_elements else None
                    
                    # Try to extract address
                    address_elements = card.find_all(['span', 'div'], class_=re.compile(r'address|location'))
                    address = address_elements[0].get_text(strip=True) if address_elements else None
                    
                    return {
                        "phone_number": phone,
                        "address": address,
                        "services_offered": [specialty]
                    }
                    
        except Exception as e:
            logger.error(f"Healthgrades search error: {str(e)}")
            
        return {}
    
    def _search_webmd(self, name: str, specialty: str, address: str = None) -> Dict:
        """
        Search WebMD physician directory using Playwright with enhanced scraping
        """
        try:
            # Check if Playwright is available and working
            if not self._is_playwright_available():
                logger.warning("Playwright is not available or compatible on this system. Skipping WebMD scraping.")
                return {}
            
            # Extract state from address if provided
            state = self._extract_state_from_address(address) if address else None
            
            # Map specialty to WebMD format
            webmd_specialty = self._map_specialty_to_webmd(specialty)
            
            # Use Playwright for WebMD scraping - run in new event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, need to run in thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._run_webmd_scraping_sync, name, webmd_specialty, state)
                        return future.result(timeout=60)  # Add timeout
                else:
                    # No event loop running, safe to use async
                    return asyncio.run(self._scrape_webmd_with_playwright(name, webmd_specialty, state))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(self._scrape_webmd_with_playwright(name, webmd_specialty, state))
                    
        except Exception as e:
            logger.error(f"WebMD search error: {str(e)}")
            logger.error(f"WebMD search traceback: {traceback.format_exc()}")
            
        return {}
    
    def _is_playwright_available(self) -> bool:
        """Check if Playwright is available and working on this system"""
        try:
            # Quick test to see if Playwright can initialize
            import subprocess
            import sys
            
            # On Windows, check if we can run playwright
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", "from playwright.async_api import async_playwright; print('OK')"],
                        capture_output=True,
                        timeout=10,
                        text=True
                    )
                    return result.returncode == 0 and "OK" in result.stdout
                except Exception:
                    return False
            else:                # On non-Windows systems, assume it works if imported successfully
                return True
                
        except Exception as e:
            logger.debug(f"Playwright availability check failed: {str(e)}")
            return False
    
    def _run_webmd_scraping_sync(self, name: str, specialty: str, state: str = None) -> Dict:
        """Run WebMD scraping in a new event loop (for thread execution)"""
        try:            # On Windows, set the appropriate event loop policy
            if platform.system() == "Windows":
                # Try to use ProactorEventLoop which supports subprocesses on Windows
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception as e:
                    logger.warning(f"Could not set Windows event loop policy: {e}")
                    return {}
            
            return asyncio.run(self._scrape_webmd_with_playwright(name, specialty, state))
        except NotImplementedError as e:
            logger.warning(f"Asyncio subprocess not supported on this system: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error in WebMD sync scraping: {e}")
            return {}
    
    def _extract_state_from_address(self, address: str) -> Optional[str]:
        """Extract state from address and convert to full name for WebMD URL"""
        if not address:
            return None
        
        # Map state abbreviations to full state names (URL format with hyphens)
        state_abbrev_to_name = {
            'AL': 'alabama', 'AK': 'alaska', 'AZ': 'arizona', 'AR': 'arkansas', 'CA': 'california',
            'CO': 'colorado', 'CT': 'connecticut', 'DE': 'delaware', 'FL': 'florida', 'GA': 'georgia',
            'HI': 'hawaii', 'ID': 'idaho', 'IL': 'illinois', 'IN': 'indiana', 'IA': 'iowa',
            'KS': 'kansas', 'KY': 'kentucky', 'LA': 'louisiana', 'ME': 'maine', 'MD': 'maryland',
            'MA': 'massachusetts', 'MI': 'michigan', 'MN': 'minnesota', 'MS': 'mississippi', 'MO': 'missouri',
            'MT': 'montana', 'NE': 'nebraska', 'NV': 'nevada', 'NH': 'new-hampshire', 'NJ': 'new-jersey',
            'NM': 'new-mexico', 'NY': 'new-york', 'NC': 'north-carolina', 'ND': 'north-dakota', 'OH': 'ohio',
            'OK': 'oklahoma', 'OR': 'oregon', 'PA': 'pennsylvania', 'RI': 'rhode-island', 'SC': 'south-carolina',
            'SD': 'south-dakota', 'TN': 'tennessee', 'TX': 'texas', 'UT': 'utah', 'VT': 'vermont',
            'VA': 'virginia', 'WA': 'washington', 'WV': 'west-virginia', 'WI': 'wisconsin', 'WY': 'wyoming'
        }
        
        # Map full state names to URL format
        state_names = {
            'alabama': 'alabama', 'alaska': 'alaska', 'arizona': 'arizona', 'arkansas': 'arkansas', 'california': 'california',
            'colorado': 'colorado', 'connecticut': 'connecticut', 'delaware': 'delaware', 'florida': 'florida', 'georgia': 'georgia',
            'hawaii': 'hawaii', 'idaho': 'idaho', 'illinois': 'illinois', 'indiana': 'indiana', 'iowa': 'iowa',
            'kansas': 'kansas', 'kentucky': 'kentucky', 'louisiana': 'louisiana', 'maine': 'maine', 'maryland': 'maryland',
            'massachusetts': 'massachusetts', 'michigan': 'michigan', 'minnesota': 'minnesota', 'mississippi': 'mississippi', 'missouri': 'missouri',
            'montana': 'montana', 'nebraska': 'nebraska', 'nevada': 'nevada', 'new hampshire': 'new-hampshire', 'new jersey': 'new-jersey',
            'new mexico': 'new-mexico', 'new york': 'new-york', 'north carolina': 'north-carolina', 'north dakota': 'north-dakota', 'ohio': 'ohio',
            'oklahoma': 'oklahoma', 'oregon': 'oregon', 'pennsylvania': 'pennsylvania', 'rhode island': 'rhode-island', 'south carolina': 'south-carolina',
            'south dakota': 'south-dakota', 'tennessee': 'tennessee', 'texas': 'texas', 'utah': 'utah', 'vermont': 'vermont',
            'virginia': 'virginia', 'washington': 'washington', 'west virginia': 'west-virginia', 'wisconsin': 'wisconsin', 'wyoming': 'wyoming'
        }
        
        # Try to find state abbreviation (2 uppercase letters)
        state_pattern = r'\b[A-Z]{2}\b'
        state_matches = re.findall(state_pattern, address.upper())
        
        if state_matches:
            state_abbrev = state_matches[-1]  # Get the last match (likely the state)
            full_state = state_abbrev_to_name.get(state_abbrev)
            if full_state:
                logger.info(f"✅ Converted state abbreviation '{state_abbrev}' -> '{full_state}'")
                return full_state
        
        # Try to match full state names in the address
        address_lower = address.lower()
        for state_name, state_url_format in state_names.items():
            if state_name in address_lower:
                logger.info(f"✅ Found full state name in address: '{state_name}' -> '{state_url_format}'")
                return state_url_format
                
        logger.warning(f"⚠️ Could not extract state from address: {address}")
        return None
    
    def _map_specialty_to_webmd(self, specialty: str) -> str:
        """Map specialty to WebMD URL format"""
        if not specialty:
            return "family-medicine"
            
        # Common specialty mappings
        specialty_mapping = {
            'family medicine': 'family-medicine',
            'internal medicine': 'internal-medicine',
            'pediatrics': 'pediatrics',
            'cardiology': 'cardiology',
            'dermatology': 'dermatology',
            'orthopedic surgery': 'orthopedic-surgery',
            'neurology': 'neurology',
            'psychiatry': 'psychiatry',
            'obstetrics and gynecology': 'obstetrics-gynecology',
            'oncology': 'oncology',
            'ophthalmology': 'ophthalmology',
            'otolaryngology': 'otolaryngology',
            'urology': 'urology',
            'radiology': 'radiology',
            'anesthesiology': 'anesthesiology',
            'emergency medicine': 'emergency-medicine',
            'pathology': 'pathology',
            'physical medicine and rehabilitation': 'physical-medicine-rehabilitation',
            'plastic surgery': 'plastic-surgery',
            'general surgery': 'general-surgery'        }
        
        specialty_lower = specialty.lower().strip()
        return specialty_mapping.get(specialty_lower, specialty_lower.replace(' ', '-').replace('&', 'and'))
    
    def _normalize_name(self, name: str) -> str:
        """Normalize doctor name for comparison"""
        if not name:
            return ""
        name = name.lower()
        name = re.sub(r"dr\.?", "", name)
        name = re.sub(r"[.,]", "", name)
        name = re.sub(r"\b(md|do|phd|dds)\b", "", name)
        name = re.sub(r"\s+", " ", name)
        
        # Handle common name variations
        # Sarah/Sara, Cathy/Kathy, etc.
        name = name.replace("sarah", "sara")  # Normalize Sarah to Sara
        
        return name.strip()
    
    def _find_doctor_in_results(self, doctors: List[Dict], target_name: str) -> Optional[Dict]:
        """Find matching doctor from scraped results with fuzzy matching"""
        target_norm = self._normalize_name(target_name)
        target_parts = target_norm.split()
        
        logger.debug(f"Looking for normalized target: '{target_norm}'")
        logger.debug(f"Target parts: {target_parts}")
        
        for doctor in doctors:
            doctor_norm = self._normalize_name(doctor["name"])
            logger.debug(f"Checking: '{doctor_norm}'")
            
            # Token-based match - all target parts should be in doctor name
            if all(part in doctor_norm for part in target_parts):
                logger.debug("✅ MATCH FOUND")
                logger.info(f"✅ Found matching doctor: {doctor['name']} -> normalized: '{doctor_norm}'")
                return doctor
        
        logger.debug("❌ No match found")
        return None
    async def _scrape_webmd_with_playwright(self, name: str, specialty: str, state: str = None) -> Dict:
        """Scrape WebMD using Playwright with the exact logic from the reference"""
        webmd_data = {
            "services_offered": [],
            "affiliated_insurance_networks": [],
            "phone_number": None,
            "address": None,
            "rating": None
        }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/121.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                    viewport={"width": 1920, "height": 1080},
                )
                
                page = await context.new_page()
                
                # Search for doctors across multiple states if no state provided
                states_to_search = [state] if state else ['idaho', 'california', 'texas', 'florida', 'new-york']
                
                doctor_found = None
                
                for search_state in states_to_search:
                    if not search_state:
                        continue
                        
                    logger.info(f"Searching WebMD in {search_state} for {name} - {specialty}")
                    
                    # Scrape doctors from WebMD
                    doctors = await self._scrape_doctors_from_webmd(page, specialty, search_state)
                    
                    if doctors:
                        # Find matching doctor
                        doctor_found = self._find_doctor_in_results(doctors, name)
                        if doctor_found:
                            logger.info(f"✅ Found matching doctor: {doctor_found['name']} in {search_state}")
                            break
                    
                    logger.info(f"No match found in {search_state}, trying next state...")
                
                if doctor_found:
                    # Get detailed information from doctor profile
                    details = await self._scrape_doctor_overview(page, doctor_found["url"])
                    
                    # Map details to our format
                    webmd_data.update({
                        "services_offered": [specialty] if specialty else [],
                        "affiliated_insurance_networks": details.get("insurance_accepted", []),
                        "phone_number": details.get("phones", [None])[0] if details.get("phones") else None,
                        "address": details.get("addresses", [None])[0] if details.get("addresses") else None,                        "rating": details.get("rating"),
                        "languages": details.get("languages", []),
                        "webmd_profile_url": doctor_found["url"]
                    })
                    
                    logger.info(f"WebMD data extracted: {len(details.get('insurance_accepted', []))} insurance plans found")
                    
                await browser.close()
                
        except Exception as e:
            logger.error(f"Playwright WebMD scraping error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return webmd_data
    
    async def _scrape_doctors_from_webmd(self, page, specialty: str, state: str, max_pages: int = 8) -> List[Dict]:
        """Scrape doctor names from WebMD search results - parallel 8 pages version"""
        base_url = f"https://doctor.webmd.com/providers/specialty/{specialty}/{state}"
        
        logger.info(f"🔍 Starting WebMD doctor name extraction (8 pages in parallel)")
        logger.info(f"📍 Target: specialty='{specialty}', state='{state}'")
        logger.info(f"🌐 Base URL: {base_url}")
        
        try:
            # Get the browser context from the page
            context = page.context
            
            # Create tasks for scraping 8 pages in parallel
            scraping_tasks = []
            for page_num in range(1, max_pages + 1):
                url = base_url if page_num == 1 else f"{base_url}?pagenumber={page_num}"
                scraping_tasks.append(self._scrape_single_page(context, url, page_num))
            
            # Execute all page scraping tasks in parallel
            logger.info(f"🚀 Launching {max_pages} parallel page scraping tasks...")
            page_results = await asyncio.gather(*scraping_tasks, return_exceptions=True)
            
            # Collect all doctors from all pages
            all_doctors = []
            successful_pages = 0
            for page_num, result in enumerate(page_results, 1):
                if isinstance(result, Exception):
                    logger.error(f"❌ Page {page_num} failed: {str(result)}")
                elif result:
                    all_doctors.extend(result)
                    successful_pages += 1
                    logger.info(f"✅ Page {page_num}: Found {len(result)} doctors")
            
            # Deduplicate by URL
            unique_doctors = list({d["url"]: d for d in all_doctors}.values())
            logger.info(f"")
            logger.info(f"{'='*60}")
            logger.info(f"🎯 PARALLEL SCRAPING COMPLETE")
            logger.info(f"📊 Pages scraped: {successful_pages}/{max_pages}")
            logger.info(f"✅ Found {len(unique_doctors)} unique doctors")
            logger.info(f"{'='*60}")
            return unique_doctors
            
        except Exception as e:
            logger.error(f"💥 Error in _scrape_doctors_from_webmd: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _scrape_single_page(self, context, url: str, page_num: int) -> List[Dict]:
        """Scrape a single WebMD search page in a new tab with lazy loading"""
        doctors = []
        new_page = None
        
        try:
            # Create a new page (tab) for this scraping task
            new_page = await context.new_page()
            
            logger.debug(f"📄 Page {page_num}: Navigating to {url}")
            await new_page.goto(url, wait_until="domcontentloaded")
            await new_page.wait_for_timeout(3000)
            
            # ✅ TRIGGER LAZY LOADING (same as POC code)
            logger.debug(f"📄 Page {page_num}: Triggering lazy loading...")
            for scroll_round in range(4):
                await new_page.mouse.wheel(0, 2500)
                await new_page.wait_for_timeout(700)
            
            logger.debug(f"📄 Page {page_num}: Lazy loading complete, parsing content...")
            
            # Get page content AFTER lazy loading
            content = await new_page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # ✅ USE CORRECT SELECTOR from POC code
            providers = soup.select("a.prov-name")
            
            logger.debug(f"📄 Page {page_num}: Found {len(providers)} provider links")
            
            if not providers:
                logger.warning(f"📄 Page {page_num}: No providers found")
                return []
            
            # Extract doctor names and URLs
            for a in providers:
                try:
                    name = a.get_text(strip=True)
                    href = a.get("href")
                    
                    if not name or not href:
                        continue
                    
                    # Ensure href is a full URL
                    if href.startswith('/'):
                        href = f"https://doctor.webmd.com{href}"
                    elif not href.startswith('http'):
                        href = f"https://doctor.webmd.com/{href}"
                    
                    doctor_entry = {
                        "name": name,
                        "url": href.split("?")[0]  # Remove query parameters
                    }
                    
                    doctors.append(doctor_entry)
                    
                except Exception as e:
                    logger.debug(f"📄 Page {page_num}: Error processing provider: {str(e)}")
                    continue
            
            return doctors
            
        except Exception as e:
            logger.error(f"❌ Page {page_num} error: {str(e)}")
            return []
        finally:
            # Close the page to free resources
            if new_page:
                try:
                    await new_page.close()
                except:
                    pass
    
    async def _scrape_doctor_overview(self, page, url: str) -> Dict:
        """Scrape detailed doctor information from profile page with enhanced logging"""
        logger.info(f"")
        logger.info(f"👤 LOADING DOCTOR PROFILE")
        logger.info(f"🔗 URL: {url}")
        
        try:
            # Load the page
            logger.debug(f"⏳ Navigating to profile page...")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for network idle with error handling
            try:
                await page.wait_for_load_state("networkidle")
                logger.debug(f"✅ Page loaded (network idle)")
            except Exception as e:
                logger.warning(f"⚠️ Network idle timeout: {str(e)[:100]}")
                logger.debug(f"⏳ Waiting 5 seconds as fallback...")
                await page.wait_for_timeout(5000)
            
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.error(f"❌ Error loading profile page: {str(e)}")
            return {}
        
        logger.debug(f"📄 Parsing profile content...")
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        logger.debug(f"📊 Profile content: {len(content):,} characters")
        
        def texts(selector):
            return [e.get_text(strip=True) for e in soup.select(selector)]
        
        def safe(selector):
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None
        
        def multi_safe(selectors):
            """Try multiple selectors and return first match"""
            for selector in selectors:
                result = safe(selector)
                if result:
                    return result
            return None
        
        def multi_texts(selectors):
            """Try multiple selectors and return first non-empty list"""
            for selector in selectors:
                result = texts(selector)
                if result:
                    return result
            return []
        
        # Get basic doctor information with enhanced selectors
        doctor_info = {
            "name": multi_safe([
                "h1", 
                ".provider-name", 
                ".doctor-name", 
                "[data-testid='provider-name']",
                ".profile-header h1"
            ]),
            "specialty": multi_safe([
                "div.Specialty", 
                ".specialty", 
                "[data-testid='specialty']",
                ".provider-specialty",
                ".doctor-specialty",
                ".profile-specialty"
            ]),
            "addresses": multi_texts([
                "address",
                ".address",
                "[data-testid='address']",
                ".provider-address",
                ".location-address"
            ]),
            "phones": multi_texts([
                "a[href^='tel']",
                ".phone",
                "[data-testid='phone']",
                ".provider-phone",
                ".contact-phone"
            ]),
            "insurance_accepted": multi_texts([
                "li[data-testid='insurance-item']",
                ".insurance-item",
                ".insurance-plan",
                ".accepted-insurance li",
                ".insurance-list li"
            ]),
            "languages": multi_texts([
                "li[data-testid='language-item']",
                ".language-item",
                ".languages li",
                ".provider-languages li"
            ]),
            "rating": multi_safe([
                "span.RatingValue",
                ".rating-value",
                "[data-testid='rating']",
                ".provider-rating",
                ".star-rating"
            ]),        }
        
        # Log extracted basic information
        logger.info(f"")
        logger.info(f"📋 EXTRACTED BASIC INFORMATION:")
        logger.info(f"   • Name:       {doctor_info['name']}")
        logger.info(f"   • Specialty:  {doctor_info['specialty']}")
        logger.info(f"   • Addresses:  {len(doctor_info['addresses'])} found")        
        logger.info(f"   • Phones:     {len(doctor_info['phones'])} found")
        logger.info(f"   • Rating:     {doctor_info['rating']}")
        logger.info(f"   • Languages:  {len(doctor_info['languages'])} found")
        logger.info(f"   • Insurance (from page): {len(doctor_info['insurance_accepted'])} plans found")
        if doctor_info['insurance_accepted']:
            logger.debug(f"      Initial insurance: {doctor_info['insurance_accepted'][:3]}...")
          # Check insurance acceptance dynamically using parallel tabs (5 insurance plans)
        insurance_plans_to_check = ["Aetna", "Blue Cross Blue Shield", "Cigna", "UnitedHealthcare", "Humana"]
        verified_insurance = []
        
        logger.info(f"")
        logger.info(f"🏥 DYNAMIC INSURANCE VERIFICATION (checking {len(insurance_plans_to_check)} plans in parallel)")
        logger.info(f"{'='*60}")
        
        # Create parallel tasks for checking all 5 insurance plans at once
        context = page.context
        insurance_check_tasks = []
        
        for insurance in insurance_plans_to_check:
            insurance_check_tasks.append(
                self._check_insurance_in_new_tab(context, url, insurance)
            )
        
        # Execute all insurance checks in parallel
        logger.info(f"🚀 Launching {len(insurance_plans_to_check)} parallel insurance verification tabs...")
        insurance_results = await asyncio.gather(*insurance_check_tasks, return_exceptions=True)
        
        # Process results
        for i, (insurance, result) in enumerate(zip(insurance_plans_to_check, insurance_results)):
            if isinstance(result, Exception):
                logger.error(f"   ⚠️ Error checking {insurance}: {str(result)[:100]}")
            elif result:
                verified_insurance.append(insurance)
                logger.info(f"   ✅ {insurance} - ACCEPTED")
            else:
                logger.info(f"   ❌ {insurance} - NOT VERIFIED/REJECTED")
        
        # Add verified insurance to the existing list
        logger.info(f"")
        logger.info(f"📊 INSURANCE VERIFICATION COMPLETE:")
        logger.info(f"   • Plans checked:  {len(insurance_plans_to_check)}")
        logger.info(f"   • Plans verified: {len(verified_insurance)}")
        if verified_insurance:
            logger.info(f"   • Accepted plans: {', '.join(verified_insurance)}")
        
        doctor_info["insurance_accepted"].extend(verified_insurance)
        # Remove duplicates while preserving order
        doctor_info["insurance_accepted"] = list(dict.fromkeys(doctor_info["insurance_accepted"]))        
        logger.info(f"   • Total insurance plans: {len(doctor_info['insurance_accepted'])}")
        logger.info(f"{'='*60}")
        
        return doctor_info
    
    async def _check_insurance_in_new_tab(self, context, url: str, insurance_name: str) -> bool:
        """
        Check insurance acceptance in a new tab/page for parallel processing
        
        Args:
            context: Browser context to create new page in
            url: Doctor profile URL
            insurance_name: Name of insurance to check
            
        Returns:
            bool: True if insurance is accepted, False otherwise
        """
        new_page = None
        try:
            # Create a new page for this insurance check
            new_page = await context.new_page()
            
            logger.debug(f"      🔍 [{insurance_name}] Opening new tab...")
            
            # Navigate to the doctor profile page
            await new_page.goto(url, wait_until="domcontentloaded")
            
            # Wait for page to be stable
            try:
                await new_page.wait_for_load_state("networkidle", timeout=5000)
            except:
                await new_page.wait_for_timeout(3000)
            
            # Scroll to find the insurance section
            logger.debug(f"      🔍 [{insurance_name}] Scrolling to insurance section...")
            await new_page.evaluate("window.scrollTo(0, 0)")
            await new_page.wait_for_timeout(500)
            
            # Scroll down to find INSURANCE PLANS ACCEPTED section
            insurance_section_found = False
            for scroll_step in range(1, 8):
                await new_page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_step / 8})")
                await new_page.wait_for_timeout(800)
                
                try:
                    insurance_text = new_page.locator("text='INSURANCE PLANS ACCEPTED'").first
                    if await insurance_text.is_visible():
                        insurance_section_found = True
                        logger.debug(f"      ✅ [{insurance_name}] Found insurance section")
                        break
                except:
                    continue
            
            if not insurance_section_found:
                logger.debug(f"      ⚠️ [{insurance_name}] Insurance section not clearly visible")
            
            # Try to find the insurance input field
            logger.debug(f"      🔍 [{insurance_name}] Looking for search input...")
            search_input_xpath = "/html/body/div[1]/main/div[4]/div[19]/div/div[2]/div/div/div[1]/div/div/div[1]/div[1]/input"
            
            try:
                search_input = new_page.locator(f"xpath={search_input_xpath}")
                await search_input.wait_for(state="visible", timeout=5000)
            except:
                # Try fallback selector
                try:
                    search_input = new_page.locator('input.webmd-input__inner[placeholder="Enter Insurance Carrier"]').first
                    await search_input.wait_for(state="visible", timeout=5000)
                except:
                    logger.debug(f"      ❌ [{insurance_name}] Input field not found")
                    return False
            
            # Enter insurance name
            logger.debug(f"      ⌨️ [{insurance_name}] Entering insurance name...")
            await search_input.click()
            await new_page.wait_for_timeout(300)
            await search_input.fill("")
            await new_page.wait_for_timeout(200)
            await search_input.type(insurance_name, delay=50)
            await new_page.wait_for_timeout(800)
            
            # Click the apply/search button
            logger.debug(f"      🖱️ [{insurance_name}] Clicking search button...")
            button_xpath = "//*[@id='insurance']/div/div[2]/div/div/div[1]/div/div/div[3]/button"
            
            try:
                apply_button = new_page.locator(f"xpath={button_xpath}")
                await apply_button.wait_for(state="visible", timeout=5000)
                await apply_button.click()
            except:
                # Fallback: press Enter
                try:
                    await search_input.press("Enter")
                except:
                    logger.debug(f"      ❌ [{insurance_name}] Could not trigger search")
                    return False
            
            # Wait for results
            await new_page.wait_for_timeout(2000)
            
            try:
                await new_page.wait_for_load_state("networkidle", timeout=5000)
            except:
                await new_page.wait_for_timeout(1000)
            
            # Check for verification text
            logger.debug(f"      🔍 [{insurance_name}] Analyzing results...")
            
            # Check for positive verification
            verify_text_selector = "div.verify-text"
            verify_elements = new_page.locator(verify_text_selector)
            
            if await verify_elements.count() > 0:
                for i in range(await verify_elements.count()):
                    verify_text = await verify_elements.nth(i).text_content()
                    if verify_text and "accepts" in verify_text.lower() and insurance_name.lower() in verify_text.lower():
                        logger.debug(f"      ✅ [{insurance_name}] ACCEPTED - verification found!")
                        return True
            
            # Check page content for acceptance patterns
            page_content = (await new_page.content()).lower()
            
            acceptance_patterns = [
                f"dr.*accepts.*{insurance_name.lower()}",
                f"accepts.*{insurance_name.lower()}",
                f"{insurance_name.lower()}.*accepted",
                f"{insurance_name.lower()}.*participating"
            ]
            
            for pattern in acceptance_patterns:
                if re.search(pattern, page_content, re.IGNORECASE):
                    logger.debug(f"      ✅ [{insurance_name}] ACCEPTED - pattern match!")
                    return True
            
            # Check for rejection patterns
            rejection_patterns = [
                "we cannot verify",
                "cannot verify",
                "not verified",
                "contact.*provider.*to confirm"
            ]
            
            for pattern in rejection_patterns:
                if re.search(pattern, page_content, re.IGNORECASE):
                    logger.debug(f"      ❌ [{insurance_name}] NOT VERIFIED")
                    return False
            
            logger.debug(f"      ⚠️ [{insurance_name}] No clear result")
            return False
            
        except Exception as e:
            logger.debug(f"      ❌ [{insurance_name}] Exception: {str(e)[:100]}")
            return False
        finally:
            # Always close the tab to free resources
            if new_page:
                try:
                    await new_page.close()
                except:
                    pass
    
    async def _check_insurance_acceptance(self, page, insurance_name: str = "Aetna") -> bool:
        """
        Check if a doctor accepts a specific insurance using the exact logic from reference
        """
        try:
            logger.debug(f"      → Verifying {insurance_name}...")
            
            # Wait for page to be stable
            try:
                await page.wait_for_load_state("networkidle")
            except:
                pass
            await page.wait_for_timeout(2000)
            
            # Scroll to find the insurance section
            logger.debug(f"      → Scrolling to find insurance section...")
            await page.evaluate("window.scrollTo(0, 0)")  # Start at top
            await page.wait_for_timeout(500)
            
            # Scroll down to find the INSURANCE PLANS ACCEPTED section
            insurance_section_found = False
            for scroll_step in range(1, 8):
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_step / 8})")
                await page.wait_for_timeout(1000)
                
                # Check if we can see "INSURANCE PLANS ACCEPTED" text
                try:
                    insurance_text = page.locator("text='INSURANCE PLANS ACCEPTED'").first
                    if await insurance_text.is_visible():
                        insurance_section_found = True
                        logger.debug(f"      → Found insurance section at scroll {scroll_step}/7")
                        break
                except:
                    continue
            
            if not insurance_section_found:
                logger.debug(f"      → Insurance section not clearly visible, continuing anyway...")
            
            # Use the exact XPath from reference code
            logger.debug(f"      → Looking for insurance input field...")
            search_input_xpath = "/html/body/div[1]/main/div[4]/div[19]/div/div[2]/div/div/div[1]/div/div/div[1]/div[1]/input"
            try:
                # Wait for the specific input field to be visible
                search_input = page.locator(f"xpath={search_input_xpath}")
                await search_input.wait_for(state="visible", timeout=5000)
                
                placeholder = await search_input.get_attribute('placeholder') or ""
                logger.debug(f"      → Found input field (placeholder: '{placeholder}')")
                
            except Exception as e:
                # Fallback to class-based selector if XPath fails
                logger.debug(f"      → XPath failed, trying fallback selector...")
                try:
                    search_input = page.locator('input.webmd-input__inner[placeholder="Enter Insurance Carrier"]').first
                    await search_input.wait_for(state="visible", timeout=5000)
                    logger.debug(f"      → Found input using fallback selector")
                except:
                    logger.debug(f"      → Input field not found: {str(e)[:100]}")
                    return False
            
            # Clear any existing text and enter insurance name
            logger.debug(f"      → Entering '{insurance_name}' in search field...")
            try:
                # Click to focus the input
                await search_input.click()
                await page.wait_for_timeout(500)
                
                # Clear existing text
                await search_input.fill("")
                await page.wait_for_timeout(300)                
                # Type the insurance name
                await search_input.type(insurance_name, delay=100)
                await page.wait_for_timeout(1000)
                
                logger.debug(f"      → Successfully entered text")
                
            except Exception as e:
                logger.debug(f"      → Failed to enter insurance name: {str(e)[:100]}")
                return False
            
            # Use the exact XPath for button from reference
            logger.debug(f"      → Clicking apply/search button...")
            button_xpath = "//*[@id='insurance']/div/div[2]/div/div/div[1]/div/div/div[3]/button"
            
            try:
                # Wait for and click the specific button
                apply_button = page.locator(f"xpath={button_xpath}")
                await apply_button.wait_for(state="visible", timeout=5000)
                await apply_button.click()
                
                logger.debug(f"      → Button clicked")
                
            except Exception as e:
                # Fallback: try pressing Enter on the input field
                logger.debug(f"      → Button failed, trying Enter key...")
                try:
                    await search_input.press("Enter")
                    logger.debug(f"      → Used Enter key")
                except Exception as enter_error:
                    logger.debug(f"      → Both methods failed: {str(e)[:100]}")
                    return False
            
            # Wait 2 seconds as requested
            await page.wait_for_timeout(2000)
            
            # Wait for any loading to complete
            logger.debug(f"      → Waiting for results...")
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except:
                await page.wait_for_timeout(1000)  # Fallback wait
              # Look for the specific verification text
            logger.debug(f"      → Analyzing verification result...")
            try:
                # Check for the positive verification message
                verify_text_selector = "div.verify-text"
                verify_elements = page.locator(verify_text_selector)
                if await verify_elements.count() > 0:
                    for i in range(await verify_elements.count()):
                        verify_text = await verify_elements.nth(i).text_content()
                        if verify_text:
                            logger.debug(f"      → Found verify text: '{verify_text[:100]}'")
                            
                            # Check if it matches the pattern "Dr. [Name], accepts [Insurance]."
                            if ("accepts" in verify_text.lower() and 
                                insurance_name.lower() in verify_text.lower()):
                                logger.debug(f"      ✅ ACCEPTED (verification found)")
                                return True
                
                # Also check for any div containing acceptance text
                page_content = (await page.content()).lower()
                
                # Look for positive acceptance patterns
                acceptance_patterns = [
                    f"dr.*accepts.*{insurance_name.lower()}",
                    f"accepts.*{insurance_name.lower()}",
                    f"{insurance_name.lower()}.*accepted",
                    f"{insurance_name.lower()}.*participating"
                ]
                
                for pattern in acceptance_patterns:
                    if re.search(pattern, page_content, re.IGNORECASE):
                        logger.debug(f"      ✅ ACCEPTED (pattern match: {pattern})")
                        return True
                
                # Check for rejection/cannot verify patterns
                rejection_patterns = [
                    "we cannot verify",
                    "cannot verify", 
                    "not verified",
                    "contact.*provider.*to confirm",
                    "you should contact the provider"
                ]
                
                for pattern in rejection_patterns:
                    if re.search(pattern, page_content, re.IGNORECASE):
                        logger.debug(f"      ❌ NOT VERIFIED (rejection: {pattern})")
                        return False
                
                # If no clear acceptance or rejection found
                logger.debug(f"      ⚠️ No clear verification result")
                return False
                
            except Exception as e:
                logger.debug(f"      ⚠️ Error checking result: {str(e)[:100]}")
                return False
            
        except Exception as e:
            logger.debug(f"      ❌ Exception: {str(e)[:100]}")
            return False
    
    def _search_google_places(self, name: str, specialty: str) -> Dict:
        """
        Search Google Places for practice information
        Requires GOOGLE_PLACES_API_KEY environment variable
        """
        google_info = {
            "practice_locations": [],
            "phone_number": None,
            "address": None,
            "google_rating": None,
            "google_reviews": []
        }
        
        try:
            # Get API key from environment
            api_key = os.getenv('GOOGLE_PLACES_API_KEY')
            
            if not api_key:
                logger.warning("Google Places API key not found. Set GOOGLE_PLACES_API_KEY environment variable.")
                logger.info("Google Places search skipped (API key required)")
                return google_info
            
            search_query = f"Dr {name} {specialty}"
            logger.info(f"Google Places search query: {search_query}")
            
            # Step 1: Text Search to find place candidates
            text_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            text_params = {
                'query': search_query,
                'key': api_key,
                'type': 'doctor'
            }
            
            response = self.session.get(text_search_url, params=text_params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('results'):
                    # Get the first result
                    place = data['results'][0]
                    place_id = place.get('place_id')
                    
                    # Step 2: Place Details to get comprehensive information
                    if place_id:
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        details_params = {
                            'place_id': place_id,
                            'key': api_key,
                            'fields': 'name,formatted_address,formatted_phone_number,rating,reviews,website,opening_hours'
                        }
                        
                        details_response = self.session.get(details_url, params=details_params, timeout=10)
                        
                        if details_response.status_code == 200:
                            details_data = details_response.json()
                            
                            if details_data.get('status') == 'OK':
                                result = details_data.get('result', {})
                                
                                google_info.update({
                                    "address": result.get('formatted_address'),
                                    "phone_number": result.get('formatted_phone_number'),
                                    "google_rating": result.get('rating'),
                                    "website": result.get('website'),
                                    "business_hours": result.get('opening_hours', {}).get('weekday_text', [])
                                })
                                
                                # Extract reviews
                                reviews = result.get('reviews', [])
                                google_info["google_reviews"] = [
                                    {
                                        "author": review.get('author_name'),
                                        "rating": review.get('rating'),
                                        "text": review.get('text'),
                                        "time": review.get('time')
                                    }
                                    for review in reviews[:5]  # Limit to 5 reviews
                                ]
                                
                                # Create practice location
                                if result.get('formatted_address'):
                                    location = {
                                        "address": result.get('formatted_address'),
                                        "phone": result.get('formatted_phone_number'),
                                        "rating": result.get('rating'),
                                        "source": "Google Places"
                                    }
                                    google_info["practice_locations"].append(location)
                                
                                logger.info(f"Google Places data found: Rating {result.get('rating')}, Reviews: {len(reviews)}")
                            else:
                                logger.warning(f"Google Places Details API error: {details_data.get('status')}")
                    else:
                        logger.warning("No place_id found in Google Places search")
                else:
                    logger.info(f"Google Places search returned no results for: {search_query}")
            else:
                logger.error(f"Google Places API request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Google Places search error: {str(e)}")
            
        return google_info
    
    def _search_medical_board(self, name: str, specialty: str) -> Dict:
        """
        Search state medical board for license information
        This is a generic implementation - would need state-specific logic
        """
        license_info = {
            "license_number": None,
            "credentials": [],
            "board_certifications": []
        }
        
        try:
            # This would need to be implemented per state
            # Each state has different medical board websites and formats
            logger.info(f"Medical board search for: {name}")
            
            # Example: Search format for various states
            # California: https://www.mbc.ca.gov/
            # New York: https://www.nysed.gov/
            # Texas: https://www.tmb.state.tx.us/
            
            # For now, we'll return placeholder info
            logger.info("Medical board search requires state-specific implementation")
            
        except Exception as e:
            logger.error(f"Medical board search error: {str(e)}")
            
        return license_info

def search_doctor_info(name: str, specialty: str, address: str = None) -> Dict:
    """
    Convenience function to search for doctor information
    
    Args:
        name (str): Doctor's full name
        specialty (str): Doctor's specialty
        address (str, optional): Doctor's address for better WebMD searching
        
    Returns:
        Dict: Comprehensive doctor information
    """
    scraper = DoctorInfoScraper()
    return scraper.get_doctor_details(name, specialty, address)

def demo_doctor_search():
    """
    Demo function to test the doctor search functionality
    """
    # Example searches
    test_cases = [
        {"name": "John Smith", "specialty": "Cardiology"},
        {"name": "Sarah Johnson", "specialty": "Dermatology"},
        {"name": "Michael Brown", "specialty": "Orthopedic Surgery"}
    ]
    
    print("=== Doctor Information Scraper Demo ===")
    
    for test_case in test_cases:
        print(f"\n🔍 Searching for: Dr. {test_case['name']} - {test_case['specialty']}")
        print("-" * 60)
        
        try:
            result = search_doctor_info(test_case['name'], test_case['specialty'])
            
            print(f"📊 Search Results:")
            print(f"   Name: {result['name']}")
            print(f"   Specialty: {result['specialty']}")
            print(f"   Sources Found: {', '.join(result['scraped_sources'])}")
            
            if result['npi_data']:
                print(f"   NPI Records: {len(result['npi_data'].get('providers', []))}")
                
            if result['address']:
                print(f"   Address: {result['address']}")
                
            if result['phone_number']:
                print(f"   Phone: {result['phone_number']}")
                
            if result['services_offered']:
                print(f"   Services: {', '.join(result['services_offered'])}")
                
            print(f"   Full data: {json.dumps(result, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error searching for {test_case['name']}: {str(e)}")            
            print(f"   ❌ Search failed: {str(e)}")
        
        time.sleep(2)  # Rate limiting

if __name__ == "__main__":
    # Run demo
    demo_doctor_search()

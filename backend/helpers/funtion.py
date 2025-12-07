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

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doctor_scraper.log'),
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
        
    def get_doctor_details(self, name: str, specialty: str) -> Dict:
        """
        Main function to get comprehensive doctor details from multiple sources
        
        Args:
            name (str): Doctor's full name
            specialty (str): Doctor's specialty/specialization
            
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
        }
        
        # Step 1: Search NPI Registry
        logger.info("Step 1: Searching NPI Registry...")
        npi_data = self._search_npi_registry(name, specialty)
        if npi_data:
            doctor_info["npi_data"] = npi_data
            doctor_info["scraped_sources"].append("NPI Registry")
            result_count = npi_data.get("result_count", 0)
            logger.info(f"NPI Registry data found: {result_count} records")
        
        # Step 2: Search Healthcare Provider Directories
        logger.info("Step 2: Searching Healthcare Provider Directories...")
        provider_data = self._search_provider_directories(name, specialty)
        if provider_data:
            doctor_info.update(provider_data)
            doctor_info["scraped_sources"].append("Provider Directories")
            
        # Step 3: Search Google Places/Maps for practice information
        logger.info("Step 3: Searching Google Places...")
        google_data = self._search_google_places(name, specialty)
        if google_data:
            doctor_info.update(google_data)
            doctor_info["scraped_sources"].append("Google Places")
            
        # Step 4: Search State Medical Board (generic approach)
        logger.info("Step 4: Searching State Medical Board information...")
        license_data = self._search_medical_board(name, specialty)
        if license_data:
            doctor_info.update(license_data)
            doctor_info["scraped_sources"].append("Medical Board")
            
        logger.info(f"Search completed. Found data from {len(doctor_info['scraped_sources'])} sources")
        return doctor_info
    
    def _search_npi_registry(self, name: str, specialty: str) -> Dict:
        """
        Search the NPI Registry using CMS API
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
                
                npi_info = []
                for result in results:
                    provider_info = {
                        "npi": result.get("number"),
                        "name": f"{result.get('basic', {}).get('first_name', '')} {result.get('basic', {}).get('last_name', '')}",
                        "credential": result.get("basic", {}).get("credential"),
                        "gender": result.get("basic", {}).get("gender"),
                        "enumeration_date": result.get("basic", {}).get("enumeration_date"),
                        "taxonomies": [tax.get("desc") for tax in result.get("taxonomies", [])],
                        "addresses": result.get("addresses", []),
                        "practice_locations": []
                    }
                    
                    # Extract practice locations
                    for addr in result.get("addresses", []):
                        if addr.get("address_purpose") == "LOCATION":
                            location = {
                                "address": f"{addr.get('address_1', '')} {addr.get('address_2', '')}".strip(),
                                "city": addr.get("city"),
                                "state": addr.get("state"),
                                "postal_code": addr.get("postal_code"),
                                "phone": addr.get("telephone_number")
                            }
                            provider_info["practice_locations"].append(location)
                    
                    npi_info.append(provider_info)
                
                # Return raw API response to match the expected structure
                return data
                
        except requests.RequestException as e:
            logger.error(f"NPI Registry search failed: {str(e)}")
        except Exception as e:
            logger.error(f"NPI Registry processing error: {str(e)}")
            
        return {}
    
    def _search_provider_directories(self, name: str, specialty: str) -> Dict:
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
            # Search Healthgrades
            healthgrades_data = self._search_healthgrades(name, specialty)
            if healthgrades_data:
                provider_info.update(healthgrades_data)
                
            # Search WebMD
            webmd_data = self._search_webmd(name, specialty)
            if webmd_data:
                # Merge data
                if webmd_data.get("services_offered"):
                    provider_info["services_offered"].extend(webmd_data["services_offered"])
                if webmd_data.get("phone_number") and not provider_info["phone_number"]:
                    provider_info["phone_number"] = webmd_data["phone_number"]
                    
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
    
    def _search_webmd(self, name: str, specialty: str) -> Dict:
        """
        Search WebMD physician directory
        """
        try:
            search_url = f"https://doctor.webmd.com/search?query={quote(name)}&specialty={quote(specialty)}"
            logger.info(f"Searching WebMD: {search_url}")
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for doctor listings
                doctor_listings = soup.find_all(['div', 'li'], class_=re.compile(r'doctor|provider|listing'))
                
                if doctor_listings:
                    listing = doctor_listings[0]
                    
                    # Extract services/specialties
                    specialty_elements = listing.find_all(['span', 'div'], class_=re.compile(r'specialty|service'))
                    services = [elem.get_text(strip=True) for elem in specialty_elements]
                    
                    return {
                        "services_offered": services if services else [specialty]
                    }
                    
        except Exception as e:
            logger.error(f"WebMD search error: {str(e)}")
            
        return {}
    
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

def search_doctor_info(name: str, specialty: str) -> Dict:
    """
    Convenience function to search for doctor information
    
    Args:
        name (str): Doctor's full name
        specialty (str): Doctor's specialty
        
    Returns:
        Dict: Comprehensive doctor information
    """
    scraper = DoctorInfoScraper()
    return scraper.get_doctor_details(name, specialty)

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
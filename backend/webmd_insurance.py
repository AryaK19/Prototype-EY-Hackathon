from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import re
import time

# ---------------- CONFIG ----------------
SPECIALTY = "family-medicine"
STATE = "idaho"
TARGET_DOCTOR_NAME = "Sara Johnson"
MAX_PAGES = 8

SEARCH_URL = f"https://doctor.webmd.com/providers/specialty/{SPECIALTY}/{STATE}"
DEBUG = True
DEBUG_PRINT_LIMIT = 20

# Insurance plans to verify dynamically
INSURANCE_PLANS_TO_CHECK = ["Aetna", "Blue Cross Blue Shield", "Cigna", "UnitedHealthcare", "Humana"]
# ----------------------------------------


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"dr\.?", "", name)
    name = re.sub(r"[.,]", "", name)
    name = re.sub(r"\b(md|do|phd|dds)\b", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def scrape_doctors(page):
    doctors = []

    for page_num in range(1, MAX_PAGES + 1):
        url = SEARCH_URL if page_num == 1 else f"{SEARCH_URL}?pagenumber={page_num}"
        print(f"Scraping page {page_num}: {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Trigger lazy loading
        for _ in range(4):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(700)

        soup = BeautifulSoup(page.content(), "html.parser")

        # ✅ CORRECT SELECTOR
        providers = soup.select("a.prov-name")

        if DEBUG:
            print(f"🔍 Found {len(providers)} provider name links on page {page_num}")

        if not providers:
            print("❌ No providers found — stopping pagination")
            break

        for a in providers:
            name = a.get_text(strip=True)
            href = a.get("href")

            if not name or not href:
                continue

            if DEBUG and len(doctors) < DEBUG_PRINT_LIMIT:
                print(f"   ➜ Scraped name: {name}")

            doctors.append({
                "name": name,
                "url": href.split("?")[0]
            })

    # Deduplicate by URL
    return list({d["url"]: d for d in doctors}.values())


def find_doctor(doctors, target):
    target_norm = normalize_name(target)
    target_parts = target_norm.split()

    if DEBUG:
        print(f"\n🎯 Target doctor (normalized): '{target_norm}'")

    for d in doctors:
        doctor_norm = normalize_name(d["name"])

        if DEBUG:
            print(f"   Checking: '{doctor_norm}'")

        # ✅ TOKEN-BASED MATCH
        if all(part in doctor_norm for part in target_parts):
            if DEBUG:
                print("   ✅ MATCH FOUND")
            return d

    if DEBUG:
        print("   ❌ No match found after checking all doctors")

    return None


def check_insurance_acceptance(page, insurance_name="Aetna"):
    """
    Check if a doctor accepts a specific insurance by using the insurance search feature
    Returns: True if accepted, False if not accepted or verification failed
    """
    try:
        if DEBUG:
            print(f"   🔍 Checking {insurance_name}...")
          # Wait for page to be stable
        try:
            page.wait_for_load_state("networkidle")
        except:
            pass
        page.wait_for_timeout(2000)
        
        # Scroll to find the insurance section
        page.evaluate("window.scrollTo(0, 0)")  # Start at top
        page.wait_for_timeout(500)
        
        # Scroll down to find the INSURANCE PLANS ACCEPTED section
        for scroll_step in range(1, 8):
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_step / 8})")
            page.wait_for_timeout(1000)
            
            # Check if we can see "INSURANCE PLANS ACCEPTED" text
            try:
                insurance_text = page.locator("text='INSURANCE PLANS ACCEPTED'").first
                if insurance_text.is_visible():
                    if DEBUG:
                        print(f"   📍 Found 'INSURANCE PLANS ACCEPTED' section at scroll step {scroll_step}")
                    break
            except:                continue
                
        # Use the exact XPath you provided for the input field
        search_input_xpath = "/html/body/div[1]/main/div[4]/div[19]/div/div[2]/div/div/div[1]/div/div/div[1]/div[1]/input"
        
        try:            # Wait for the specific input field to be visible
            search_input = page.locator(f"xpath={search_input_xpath}")
            search_input.wait_for(state="visible")
            
            if DEBUG:
                placeholder = search_input.get_attribute('placeholder') or ""
                current_value = search_input.get_attribute('value') or ""
                print(f"   📍 Found insurance input with placeholder: '{placeholder}', current value: '{current_value}'")
            
        except Exception as e:
            # Fallback to class-based selector if XPath fails
            try:
                search_input = page.locator('input.webmd-input__inner[placeholder="Enter Insurance Carrier"]').first
                search_input.wait_for(state="visible")
                if DEBUG:
                    print(f"   📍 Found insurance input using fallback selector")
            except:
                if DEBUG:
                    print(f"   ❌ Could not find insurance input field: {str(e)}")
                return False
        
        # Clear any existing text and enter insurance name
        try:
            # Click to focus the input
            search_input.click()
            page.wait_for_timeout(500)
            
            # Clear existing text
            search_input.fill("")
            page.wait_for_timeout(300)
            
            # Type the insurance name
            search_input.type(insurance_name, delay=100)
            page.wait_for_timeout(1000)
            
            if DEBUG:
                print(f"   📝 Entered '{insurance_name}' in search field")
            
        except Exception as e:
            if DEBUG:
                print(f"   ❌ Failed to enter insurance name: {str(e)}")
            return False
        
        # Use the exact XPath you provided for the button
        button_xpath = "//*[@id='insurance']/div/div[2]/div/div/div[1]/div/div/div[3]/button"
        
        try:
            # Wait for and click the specific button
            apply_button = page.locator(f"xpath={button_xpath}")
            apply_button.wait_for(state="visible")
            apply_button.click()
            
            if DEBUG:
                print(f"   🔘 Clicked search/apply button")
            
        except Exception as e:
            # Fallback: try pressing Enter on the input field
            try:
                search_input.press("Enter")
                if DEBUG:
                    print(f"   📍 Used Enter key as fallback")
            except Exception as enter_error:
                if DEBUG:
                    print(f"   ❌ Button click and Enter both failed: {str(e)}")
                return False
        
        # Wait 2 seconds as requested
        page.wait_for_timeout(2000)
          # Wait for any loading to complete
        try:
            page.wait_for_load_state("networkidle")
        except:
            page.wait_for_timeout(1000)  # Fallback wait
          # Look for the specific verification text you mentioned
        try:
            # Check for the positive verification message in the exact format you specified
            # <div class="verify-text">Dr. {Doctor name}, accepts {insurance name}.</div>
            verify_text_selector = "div.verify-text"
            verify_elements = page.locator(verify_text_selector)
            
            if verify_elements.count() > 0:
                for i in range(verify_elements.count()):
                    verify_text = verify_elements.nth(i).text_content()
                    if verify_text:
                        if DEBUG:
                            print(f"   📋 Found verify text: '{verify_text}'")
                        
                        # Check if it matches the pattern "Dr. [Name], accepts [Insurance]."
                        if ("accepts" in verify_text.lower() and 
                            insurance_name.lower() in verify_text.lower()):
                            if DEBUG:
                                print(f"   ✅ {insurance_name} - ACCEPTED (found verification: '{verify_text}')")
                            return True
            
            # Also check for any div containing acceptance text
            page_content = page.content().lower()
            
            # Look for positive acceptance patterns
            acceptance_patterns = [
                f"dr.*accepts.*{insurance_name.lower()}",
                f"accepts.*{insurance_name.lower()}",
                f"{insurance_name.lower()}.*accepted",
                f"{insurance_name.lower()}.*participating"
            ]
            
            for pattern in acceptance_patterns:
                if re.search(pattern, page_content, re.IGNORECASE):
                    if DEBUG:
                        print(f"   ✅ {insurance_name} - ACCEPTED (found pattern: {pattern})")
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
                    if DEBUG:
                        print(f"   ❌ {insurance_name} - NOT VERIFIED (found rejection: {pattern})")
                    return False
            
            # If no clear acceptance or rejection found
            if DEBUG:
                print(f"   ⚠️  {insurance_name} - No clear verification result found")
            return False
            
        except Exception as e:
            if DEBUG:
                print(f"   ❌ Error checking verification result: {str(e)}")
            return False
        
    except Exception as e:
        if DEBUG:
            print(f"   ❌ Error checking {insurance_name}: {str(e)}")
        return False


def scrape_doctor_overview(page, url):
    try:
        if DEBUG:
            print(f"\n🔗 Loading doctor profile: {url}")
          # Go to the page
        page.goto(url, wait_until="domcontentloaded")
          # Wait for network idle with error handling
        try:
            page.wait_for_load_state("networkidle")
        except Exception as e:
            if DEBUG:
                print(f"   ⚠️  Network idle timeout, continuing anyway: {str(e)}")
            # Continue with a simple timeout instead
            page.wait_for_timeout(5000)
        
        page.wait_for_timeout(2000)  # Additional wait for dynamic content
        
    except Exception as e:
        if DEBUG:
            print(f"   ❌ Error loading page: {str(e)}")
        return {
            "name": "Error loading page",
            "specialty": None,
            "addresses": [],
            "phones": [],
            "insurance_accepted": [],
            "languages": [],
            "rating": None
        }

    soup = BeautifulSoup(page.content(), "html.parser")

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
        ]),    }

    # Check insurance acceptance dynamically
    verified_insurance = []
    
    if DEBUG:
        print(f"\n🔍 Checking insurance acceptance for {doctor_info['name']}...")
    
    for i, insurance in enumerate(INSURANCE_PLANS_TO_CHECK):
        try:
            # Reload the page before each insurance check to reset the page state
            if i > 0:  # Don't reload on first check since we just loaded the page
                if DEBUG:
                    print(f"   🔄 Reloading page for {insurance} check...")
                page.goto(url, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle")
                except:
                    page.wait_for_timeout(3000)  # Fallback timeout
            
            if check_insurance_acceptance(page, insurance):
                verified_insurance.append(insurance)
                if DEBUG:
                    print(f"   ✅ {insurance} - ACCEPTED")
            else:
                if DEBUG:
                    print(f"   ❌ {insurance} - NOT VERIFIED/REJECTED")
                    
        except Exception as e:
            if DEBUG:
                print(f"   ❌ Error checking {insurance}: {str(e)}")
            continue
    
    # Add verified insurance to the existing list
    doctor_info["insurance_accepted"].extend(verified_insurance)
    # Remove duplicates while preserving order
    doctor_info["insurance_accepted"] = list(dict.fromkeys(doctor_info["insurance_accepted"]))
    
    return doctor_info


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1920, "height": 1080},
        )

        page = context.new_page()

        doctors = scrape_doctors(page)
        print(f"\nTotal doctors scraped: {len(doctors)}")

        doctor = find_doctor(doctors, TARGET_DOCTOR_NAME)
        if not doctor:
            print("\n❌ Doctor not found")
            return        print("\n✅ Matched doctor:", doctor["name"])
        print("Profile URL:", doctor["url"])

        details = scrape_doctor_overview(page, doctor["url"])
        print("\nDoctor Overview:")
        for k, v in details.items():
            if k == "insurance_accepted" and v:
                print(f"{k}: {', '.join(v)} (Total: {len(v)} plans)")
            else:
                print(f"{k}: {v}")

        browser.close()


if __name__ == "__main__":
    main()

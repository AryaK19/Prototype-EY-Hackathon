from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import re
import time

# ---------------- CONFIG ----------------
SPECIALTY = "family-medicine"
STATE = "idaho"
TARGET_DOCTOR_NAME = "Kenneth Romney"
MAX_PAGES = 5

SEARCH_URL = f"https://doctor.webmd.com/providers/specialty/{SPECIALTY}/{STATE}"
DEBUG = True
DEBUG_PRINT_LIMIT = 20
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

        page.goto(url, timeout=90000, wait_until="domcontentloaded")
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


def scrape_doctor_overview(page, url):
    page.goto(url, timeout=90000, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    soup = BeautifulSoup(page.content(), "html.parser")

    def texts(selector):
        return [e.get_text(strip=True) for e in soup.select(selector)]

    def safe(selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    return {
        "name": safe("h1"),
        "specialty": safe("div.Specialty"),
        "addresses": texts("address"),
        "phones": texts("a[href^='tel']"),
        "insurance_accepted": texts("li[data-testid='insurance-item']"),
        "languages": texts("li[data-testid='language-item']"),
        "rating": safe("span.RatingValue"),
    }


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
            return

        print("\n✅ Matched doctor:", doctor["name"])
        print("Profile URL:", doctor["url"])

        details = scrape_doctor_overview(page, doctor["url"])
        print("\nDoctor Overview:")
        for k, v in details.items():
            print(f"{k}: {v}")

        browser.close()


if __name__ == "__main__":
    main()

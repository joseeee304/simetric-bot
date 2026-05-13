import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

MIN_M2 = 400
MAX_M2 = 1500

COLONIAS = [
    "del-valle-norte", "del-valle-centro", "roma-norte", "roma-sur",
    "napoles", "cuauhtemoc", "juarez", "ciudad-de-los-deportes",
    "san-rafael", "tabacalera", "condesa", "hipodromo",
    "hipodromo-condesa", "anzures"
]

COLONIAS_DISPLAY = {
    "del-valle-norte": "Del Valle Norte",
    "del-valle-centro": "Del Valle Centro",
    "roma-norte": "Roma Norte",
    "roma-sur": "Roma Sur",
    "napoles": "Napoles",
    "cuauhtemoc": "Cuauhtemoc",
    "juarez": "Juarez",
    "ciudad-de-los-deportes": "Ciudad de los Deportes",
    "san-rafael": "San Rafael",
    "tabacalera": "Tabacalera",
    "condesa": "Condesa",
    "hipodromo": "Hipodromo",
    "hipodromo-condesa": "Hipodromo Condesa",
    "anzures": "Anzures",
}


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    from selenium.webdriver.chrome.service import Service
    service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def parse_number(text):
    if not text:
        return None
    nums = re.findall(r'\d+', str(text).replace(',', ''))
    if nums:
        try:
            return float(nums[0])
        except:
            return None
    return None


def make_listing(portal, title, price_text, area_text, link, colonia):
    price = parse_number(price_text)
    area = parse_number(area_text)
    if area and (area < MIN_M2 or area > MAX_M2):
        return None
    return {
        "id": f"{portal[:4]}_{abs(hash(link)) % 9999999}",
        "portal": portal,
        "colonia": colonia,
        "title": (title or "Terreno")[:100],
        "price": price,
        "price_text": price_text or "",
        "area": area,
        "area_text": area_text or "",
        "frente": None,
        "link": link,
    }


def scrape_inmuebles24(driver, colonia):
    results = []
    url = f"https://www.inmuebles24.com/terrenos-en-venta-en-{colonia}-ciudad-de-mexico.html"
    try:
        driver.get(url)
        time.sleep(4)
        page_source = driver.page_source

        # Debug: show what selectors find
        s1 = driver.find_elements(By.CSS_SELECTOR, '[data-qa="posting PROPERTY"]')
        s2 = driver.find_elements(By.CSS_SELECTOR, '.listing-card')
        s3 = driver.find_elements(By.CSS_SELECTOR, '[class*="posting"]')
        s4 = driver.find_elements(By.CSS_SELECTOR, 'article')
        print(f"    [I24] {colonia}: s1={len(s1)} s2={len(s2)} s3={len(s3)} s4={len(s4)}")

        listings = s1 or s2 or s3 or s4

        for item in listings[:10]:
            try:
                title = item.text[:80] if item.text else "Terreno"
                links = item.find_elements(By.TAG_NAME, 'a')
                link = links[0].get_attribute('href') if links else url
                l = make_listing("Inmuebles24", title, "", "", link, COLONIAS_DISPLAY.get(colonia, colonia))
                if l:
                    results.append(l)
            except Exception:
                continue
    except Exception as e:
        print(f"    [I24] Error {colonia}: {e}")
    return results


def scrape_all():
    all_results = []
    print("  [Selenium scraper iniciando...]")
    driver = None
    try:
        driver = get_driver()
        print("  [Chrome OK]")
        for colonia in COLONIAS:
            print(f"  Scraping {COLONIAS_DISPLAY.get(colonia, colonia)}...")
            r = scrape_inmuebles24(driver, colonia)
            all_results.extend(r)
            time.sleep(2)
        print(f"  Total bruto: {len(all_results)}")
    except Exception as e:
        print(f"  [Error]: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
    return all_results

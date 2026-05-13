import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MIN_M2 = 400
MAX_M2 = 1500
MIN_FRENTE = 14

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
    "napoles": "Nápoles",
    "cuauhtemoc": "Cuauhtémoc",
    "juarez": "Juárez",
    "ciudad-de-los-deportes": "Ciudad de los Deportes",
    "san-rafael": "San Rafael",
    "tabacalera": "Tabacalera",
    "condesa": "Condesa",
    "hipodromo": "Hipódromo",
    "hipodromo-condesa": "Hipódromo Condesa",
    "anzures": "Anzures",
}


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")

    from selenium.webdriver.chrome.service import Service
    service = Service(os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def parse_number(text):
    if not text:
        return None
    nums = re.findall(r'[\d,\.]+', str(text).replace(',', ''))
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
        time.sleep(3)

        # Wait for listings to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qa="posting PROPERTY"]'))
            )
        except:
            pass

        listings = driver.find_elements(By.CSS_SELECTOR, '[data-qa="posting PROPERTY"]')
        if not listings:
            listings = driver.find_elements(By.CSS_SELECTOR, '.listing-card')

        for item in listings[:10]:
            try:
                title_el = item.find_elements(By.CSS_SELECTOR, '[data-qa="posting-title"]')
                price_el = item.find_elements(By.CSS_SELECTOR, '[data-qa="price"]')
                area_el = item.find_elements(By.CSS_SELECTOR, '[data-qa="surface-area"]')
                link_el = item.find_elements(By.TAG_NAME, 'a')

                title = title_el[0].text if title_el else "Terreno"
                price_text = price_el[0].text if price_el else ""
                area_text = area_el[0].text if area_el else ""
                link = link_el[0].get_attribute('href') if link_el else url

                l = make_listing("Inmuebles24", title, price_text, area_text, link, COLONIAS_DISPLAY.get(colonia, colonia))
                if l:
                    results.append(l)
            except Exception:
                continue

    except Exception as e:
        print(f"    [I24] Error {colonia}: {e}")
    return results


def scrape_vivanuncios(driver, colonia):
    results = []
    url = f"https://www.vivanuncios.com.mx/s-terrenos-en-venta/{colonia}/v1c1117l10201p1"
    try:
        driver.get(url)
        time.sleep(3)

        listings = driver.find_elements(By.CSS_SELECTOR, '.ad-listing')
        if not listings:
            listings = driver.find_elements(By.CSS_SELECTOR, '[data-id]')

        for item in listings[:10]:
            try:
                title_el = item.find_elements(By.TAG_NAME, 'h2')
                price_el = item.find_elements(By.CSS_SELECTOR, '.price')
                link_el = item.find_elements(By.TAG_NAME, 'a')

                title = title_el[0].text if title_el else "Terreno"
                price_text = price_el[0].text if price_el else ""
                link = link_el[0].get_attribute('href') if link_el else url

                l = make_listing("Vivanuncios", title, price_text, "", link, COLONIAS_DISPLAY.get(colonia, colonia))
                if l:
                    results.append(l)
            except Exception:
                continue

    except Exception as e:
        print(f"    [VV] Error {colonia}: {e}")
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

            r1 = scrape_inmuebles24(driver, colonia)
            all_results.extend(r1)
            time.sleep(2)

            r2 = scrape_vivanuncios(driver, colonia)
            all_results.extend(r2)
            time.sleep(2)

        print(f"  Total: {len(all_results)} terrenos encontrados")

    except Exception as e:
        print(f"  [Selenium error]: {e}")
        import traceback; traceback.print_exc()
    finally:
        if driver:
            driver.quit()

    return all_results

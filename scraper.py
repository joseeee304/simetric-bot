import requests
from bs4 import BeautifulSoup
import re
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

COLONIAS_SLUG = [
    "del-valle-norte", "del-valle-centro", "roma-norte", "roma-sur",
    "napoles", "cuauhtemoc", "juarez", "ciudad-de-los-deportes",
    "san-rafael", "tabacalera", "condesa", "hipodromo",
    "hipodromo-condesa", "anzures"
]

COLONIAS_DISPLAY = {
    "del-valle-norte": "Del Valle Norte", "del-valle-centro": "Del Valle Centro",
    "roma-norte": "Roma Norte", "roma-sur": "Roma Sur",
    "napoles": "Nápoles", "cuauhtemoc": "Cuauhtémoc",
    "juarez": "Juárez", "ciudad-de-los-deportes": "Cd. de los Deportes",
    "san-rafael": "San Rafael", "tabacalera": "Tabacalera",
    "condesa": "Condesa", "hipodromo": "Hipódromo",
    "hipodromo-condesa": "Hipódromo Condesa", "anzures": "Anzures"
}

MIN_M2 = 400
MAX_M2 = 1500


def parse_number(text):
    if not text:
        return None
    clean = re.sub(r'[,$\s]', '', str(text))
    nums = re.findall(r'\d+\.?\d*', clean)
    if nums:
        try:
            return float(nums[0])
        except:
            return None
    return None


def make_listing(portal, colonia_slug, title, price_text, area_text, link):
    price = parse_number(price_text)
    area = parse_number(area_text)
    if area and (area < MIN_M2 or area > MAX_M2):
        return None
    uid = f"{portal[:4]}_{colonia_slug}_{abs(hash(link)) % 9999999}"
    return {
        "id": uid,
        "portal": portal,
        "colonia": COLONIAS_DISPLAY.get(colonia_slug, colonia_slug),
        "title": (title or "Terreno")[:100],
        "price": price,
        "price_text": price_text or "",
        "area": area,
        "area_text": area_text or "",
        "link": link,
    }


def get_soup(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"    [error] {url[:55]}: {e}")
    return None


def sleep():
    time.sleep(random.uniform(2.0, 4.5))


def scrape_inmuebles24(colonia):
    results = []
    url = f"https://www.inmuebles24.com/terrenos-en-venta-en-{colonia}-ciudad-de-mexico.html"
    soup = get_soup(url)
    if not soup: return results
    for item in soup.select('[data-qa="posting PROPERTY"]')[:15]:
        try:
            t = item.select_one('[data-qa="posting-title"]') or item.select_one("h2")
            p = item.select_one('[data-qa="price"]') or item.select_one(".firstPrice")
            a = item.select_one('[data-qa="surface-area"]')
            le = item.select_one("a[href]")
            link = ("https://www.inmuebles24.com" + le["href"]) if le and le["href"].startswith("/") else (le["href"] if le else url)
            l = make_listing("Inmuebles24", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_vivanuncios(colonia):
    results = []
    url = f"https://www.vivanuncios.com.mx/s-terrenos-en-venta/{colonia}/v1c1117l10201p1"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select(".ad-listing") or soup.select('[data-id]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one(".title")
            p = item.select_one(".price") or item.select_one('[class*="price"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.vivanuncios.com.mx" + link
            l = make_listing("Vivanuncios", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_lamudi(colonia):
    results = []
    url = f"https://www.lamudi.com.mx/distrito-federal/{colonia}/terreno/for-sale/"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select(".js-listing-item") or soup.select('[class*="ListingCell"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]')
            a = item.select_one('[title*="m"]') or item.select_one('[class*="area"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.lamudi.com.mx" + link
            l = make_listing("Lamudi", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_mercadolibre(colonia):
    results = []
    url = f"https://inmuebles.mercadolibre.com.mx/terrenos/venta/{colonia}-df/"
    soup = get_soup(url)
    if not soup: return results
    for item in soup.select(".ui-search-result__wrapper")[:15]:
        try:
            t = item.select_one(".ui-search-item__title") or item.select_one("h2")
            p = item.select_one(".price-tag-fraction")
            sym = item.select_one(".price-tag-symbol")
            a = item.select_one('[class*="attribute"]')
            le = item.select_one("a.ui-search-link") or item.select_one("a[href]")
            link = le["href"] if le else url
            pt = f"{sym.get_text() if sym else '$'}{p.get_text(strip=True)}" if p else ""
            l = make_listing("MercadoLibre", colonia, t.get_text(strip=True) if t else "", pt, a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_propiedades(colonia):
    results = []
    url = f"https://propiedades.com/df/{colonia}/terrenos-venta"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select(".property-item") or soup.select('[class*="propiedad"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one("h3")
            p = item.select_one('[class*="price"]') or item.select_one(".precio")
            a = item.select_one('[class*="area"]') or item.select_one('[class*="m2"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://propiedades.com" + link
            l = make_listing("Propiedades.com", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_metroscubicos(colonia):
    results = []
    url = f"https://www.metroscubicos.com/terrenos/df/{colonia}/venta"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select(".listing-item") or soup.select('[class*="property"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]') or item.select_one(".precio")
            a = item.select_one('[class*="surface"]') or item.select_one('[class*="area"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.metroscubicos.com" + link
            l = make_listing("MetrosCúbicos", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_easybroker(colonia):
    results = []
    url = f"https://www.easybroker.com/mx/propiedades/terrenos?neighborhood={colonia}&city=Ciudad+de+Mexico&operation_type=sale"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select('[class*="property-card"]') or soup.select('[class*="listing"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]')
            a = item.select_one('[class*="area"]') or item.select_one('[class*="lot"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.easybroker.com" + link
            l = make_listing("EasyBroker", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_century21(colonia):
    results = []
    url = f"https://www.century21mexico.com/buscar?tipo=terreno&operacion=venta&colonia={colonia}&ciudad=ciudad-de-mexico"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select(".property-card") or soup.select('[class*="listing"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]') or item.select_one(".precio")
            a = item.select_one('[class*="area"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.century21mexico.com" + link
            l = make_listing("Century21", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_remax(colonia):
    results = []
    url = f"https://www.remax.com.mx/listings/buy?city=Ciudad+de+Mexico&neighborhood={colonia.replace('-','+')}&propertyType=LND"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select('[class*="listing-card"]') or soup.select('[class*="property"]'))[:15]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]')
            a = item.select_one('[class*="lot"]') or item.select_one('[class*="area"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.remax.com.mx" + link
            l = make_listing("RE/MAX", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_coldwell(colonia):
    results = []
    url = f"https://www.coldwellbanker.com.mx/buscar/venta/terreno/ciudad-de-mexico/{colonia}"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select('[class*="property"]') or soup.select('[class*="listing"]'))[:10]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]') or item.select_one(".precio")
            a = item.select_one('[class*="area"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.coldwellbanker.com.mx" + link
            l = make_listing("Coldwell Banker", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", a.get_text(strip=True) if a else "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_olx(colonia):
    results = []
    url = f"https://www.olx.com.mx/inmuebles_cat_357/{colonia}-ciudad-de-mexico"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select('[data-aut-id="itemBox"]') or soup.select('.EIR5N'))[:15]:
        try:
            t = item.select_one('[data-aut-id="itemTitle"]') or item.select_one("span")
            p = item.select_one('[data-aut-id="itemPrice"]') or item.select_one('[class*="price"]')
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            l = make_listing("OLX", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", "", link)
            if l: results.append(l)
        except: continue
    return results


def scrape_era(colonia):
    results = []
    url = f"https://www.eraimmobiliaria.com.mx/propiedades?tipo=terreno&operacion=venta&colonia={colonia}"
    soup = get_soup(url)
    if not soup: return results
    for item in (soup.select('[class*="property"]') or soup.select('[class*="card"]'))[:10]:
        try:
            t = item.select_one("h2") or item.select_one('[class*="title"]')
            p = item.select_one('[class*="price"]') or item.select_one(".precio")
            le = item.select_one("a[href]")
            link = le["href"] if le else url
            if link.startswith("/"): link = "https://www.eraimmobiliaria.com.mx" + link
            l = make_listing("ERA", colonia, t.get_text(strip=True) if t else "", p.get_text(strip=True) if p else "", "", link)
            if l: results.append(l)
        except: continue
    return results


SCRAPERS = [
    ("Inmuebles24",     scrape_inmuebles24),
    ("Vivanuncios",     scrape_vivanuncios),
    ("Lamudi",          scrape_lamudi),
    ("MercadoLibre",    scrape_mercadolibre),
    ("Propiedades.com", scrape_propiedades),
    ("MetrosCúbicos",   scrape_metroscubicos),
    ("EasyBroker",      scrape_easybroker),
    ("Century21",       scrape_century21),
    ("RE/MAX",          scrape_remax),
    ("Coldwell Banker", scrape_coldwell),
    ("OLX",             scrape_olx),
    ("ERA",             scrape_era),
]


def scrape_all():
    all_results = []
    for portal_name, fn in SCRAPERS:
        print(f"\n  [{portal_name}]")
        for colonia in COLONIAS_SLUG:
            try:
                results = fn(colonia)
                all_results.extend(results)
                if results:
                    print(f"    ✓ {colonia}: {len(results)}")
            except Exception as e:
                print(f"    ✗ {colonia}: {e}")
            sleep()
    print(f"\n  Total: {len(all_results)} listings")
    return all_results

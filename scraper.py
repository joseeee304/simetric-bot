import requests
import time
import os

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "es-MX"}

MIN_M2 = 400
MAX_M2 = 1500
MIN_FRENTE = 14

ML_CLIENT_ID = os.environ.get("ML_CLIENT_ID", "")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET", "")
EASYBROKER_KEY = os.environ.get("EASYBROKER_API_KEY", "")

_ml_token = None
_ml_token_expiry = 0

# Neighborhood IDs from MercadoLibre API - exact matches for target colonias
NEIGHBORHOODS = {
    # Benito Juárez
    "Del Valle Centro":          "TUxNQkRFTEEwN0U",
    "Del Valle Norte":           "TUxNTUxNQkRFTEFKQg",
    "Nápoles":                   "TUxNQk7BUDUwNzQ",
    "Ciudad de los Deportes":    "TUxNQkNJVTYzMDc",
    "Colonia Del Valle":         "TUxNQkRFTDY3NTg",
    # Cuauhtémoc - get from that city
    # Miguel Hidalgo - get from that city
}

# City IDs to search
CITY_IDS = {
    "Benito Juárez":   "TUxNQ0JFTjM2MjQ",
    "Cuauhtémoc":      "TUxNQ0NVQTczMTI",
    "Miguel Hidalgo":  "TUxNQ01JRzU0Mjg",
}

# MLM real estate category for terrenos
ML_CATEGORY = "MLM1473"


def get_ml_token():
    global _ml_token, _ml_token_expiry
    now = time.time()
    if _ml_token and now < _ml_token_expiry:
        return _ml_token
    try:
        r = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": ML_CLIENT_ID,
                "client_secret": ML_CLIENT_SECRET,
            },
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            _ml_token = data.get("access_token")
            _ml_token_expiry = now + data.get("expires_in", 21600) - 300
            print(f"  [ML] Token OK")
            return _ml_token
        else:
            print(f"  [ML] Token error: {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"  [ML] Token error: {e}")
    return None


def get_neighborhoods_for_city(city_id, token):
    """Fetch all neighborhoods for a city from ML API."""
    try:
        r = requests.get(
            f"https://api.mercadolibre.com/classified_locations/cities/{city_id}",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("neighborhoods", [])
    except Exception as e:
        print(f"  [ML] Error fetching neighborhoods: {e}")
    return []


TARGET_COLONIAS = [
    "del valle norte", "del valle centro", "roma norte", "roma sur",
    "napoles", "nápoles", "cuauhtémoc", "cuauhtemoc", "juárez", "juarez",
    "ciudad de los deportes", "san rafael", "tabacalera", "condesa",
    "hipódromo", "hipodromo", "hipódromo condesa", "hipodromo condesa", "anzures"
]


def matches_target(name):
    if not name:
        return False
    n = name.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    for c in TARGET_COLONIAS:
        c2 = c.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        if c2 in n or n in c2:
            return True
    return False


def make_listing(portal, title, price, price_text, area, frente, link, colonia=""):
    return {
        "id": f"{portal[:4]}_{abs(hash(link)) % 9999999}",
        "portal": portal,
        "colonia": colonia,
        "title": (title or "Terreno")[:100],
        "price": price,
        "price_text": price_text or "",
        "area": area,
        "frente": frente,
        "link": link,
    }


def passes_filters(area, frente):
    if area and (area < MIN_M2 or area > MAX_M2):
        return False
    if frente and frente < MIN_FRENTE:
        return False
    return True


def search_by_neighborhood(neighborhood_id, neighborhood_name, token):
    """Search terrenos in a specific neighborhood."""
    results = []
    try:
        url = (
            f"https://api.mercadolibre.com/sites/MLM/search"
            f"?category={ML_CATEGORY}"
            f"&neighborhood={neighborhood_id}"
            f"&limit=50"
        )
        r = requests.get(url, headers={**HEADERS, "Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code != 200:
            # Try with state filter
            url2 = (
                f"https://api.mercadolibre.com/sites/MLM/search"
                f"?category={ML_CATEGORY}"
                f"&state=TUxNUERJUzYwOTQ"
                f"&city={neighborhood_id}"
                f"&limit=50"
            )
            r = requests.get(url2, headers={**HEADERS, "Authorization": f"Bearer {token}"}, timeout=15)
            if r.status_code != 200:
                return results

        items = r.json().get("results", [])
        for item in items:
            try:
                title = item.get("title", "")
                price = item.get("price")
                link = item.get("permalink", "")
                currency = item.get("currency_id", "MXN")
                price_text = f"${price:,.0f} {currency}" if price else ""

                area = None
                frente = None

                for attr in item.get("attributes", []):
                    attr_id = attr.get("id", "")
                    val = attr.get("value_name", "") or ""
                    if attr_id in ("TOTAL_AREA", "LOT_SIZE", "SURFACE_TOTAL"):
                        try: area = float(str(val).replace(",","").replace("m²","").strip())
                        except: pass
                    elif attr_id == "LOT_FRONTAGE":
                        try: frente = float(str(val).replace("m","").strip())
                        except: pass

                if not passes_filters(area, frente):
                    continue

                results.append(make_listing(
                    "MercadoLibre", title, price, price_text,
                    area, frente, link, neighborhood_name
                ))
            except Exception:
                continue

    except Exception as e:
        print(f"    Error {neighborhood_name}: {e}")
    return results


def scrape_mercadolibre_api():
    results = []
    print("  [MercadoLibre API]")

    token = get_ml_token()
    if not token:
        print("    Sin token — skip")
        return results

    # Get neighborhoods for each target city and filter by target colonias
    all_target_neighborhoods = {}

    for city_name, city_id in CITY_IDS.items():
        neighborhoods = get_neighborhoods_for_city(city_id, token)
        for nb in neighborhoods:
            if matches_target(nb.get("name", "")):
                all_target_neighborhoods[nb["id"]] = nb["name"]
                print(f"    ✓ Colonia encontrada: {nb['name']}")
        time.sleep(0.3)

    print(f"  Buscando en {len(all_target_neighborhoods)} colonias...")

    # Search terrenos in each target neighborhood
    for nb_id, nb_name in all_target_neighborhoods.items():
        found = search_by_neighborhood(nb_id, nb_name, token)
        results.extend(found)
        if found:
            print(f"    {nb_name}: {len(found)} terrenos")
        time.sleep(0.5)

    print(f"    Total ML: {len(results)} terrenos")
    return results


def scrape_easybroker_api():
    results = []
    if not EASYBROKER_KEY:
        return results

    print("  [EasyBroker API]")
    page = 1
    while page <= 5:
        try:
            r = requests.get(
                f"https://api.easybroker.com/v1/properties"
                f"?operation_type=sale&property_type=land"
                f"&location=Ciudad+de+Mexico&page={page}&per_page=50",
                headers={**HEADERS, "X-Authorization": EASYBROKER_KEY},
                timeout=15
            )
            if r.status_code != 200:
                break
            items = r.json().get("content", [])
            if not items:
                break
            for item in items:
                try:
                    title = item.get("title", "Terreno")
                    price = item.get("asking_price")
                    price_text = f"${price:,.0f} MXN" if price else ""
                    link = item.get("public_url", "")
                    area = item.get("lot_size") or item.get("construction_size")
                    nb = (item.get("location") or {}).get("neighborhood", "") or ""
                    colonia = nb if matches_target(nb) else ""
                    if not colonia or not passes_filters(area, None):
                        continue
                    results.append(make_listing(
                        "EasyBroker", title, price, price_text,
                        area, None, link, colonia
                    ))
                except Exception:
                    continue
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"    EB error: {e}")
            break

    print(f"    Total EB: {len(results)} terrenos")
    return results


def scrape_all():
    all_results = []
    all_results.extend(scrape_mercadolibre_api())
    all_results.extend(scrape_easybroker_api())
    print(f"\n  Total: {len(all_results)} terrenos que cumplen filtros")
    return all_results

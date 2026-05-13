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


COLONIAS_DISPLAY = [
    "Del Valle Norte", "Del Valle Centro", "Roma Norte", "Roma Sur",
    "Nápoles", "Cuauhtémoc", "Juárez", "Ciudad de los Deportes",
    "San Rafael", "Tabacalera", "Condesa", "Hipódromo",
    "Hipódromo Condesa", "Anzures"
]


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


def colonia_match(text):
    if not text:
        return ""
    text_lower = text.lower()
    for c in COLONIAS_DISPLAY:
        if c.lower() in text_lower:
            return c
        parts = c.lower().split()
        if len(parts) > 1 and all(p in text_lower for p in parts):
            return c
    return ""


def scrape_mercadolibre_api():
    results = []
    print("  [MercadoLibre API]")

    token = get_ml_token()
    if not token:
        print("    Sin token — skip")
        return results

    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}

    # CDMX bounding box coordinates
    # lat: 19.20 to 19.60, lon: -99.35 to -98.95
    searches = [
        "terreno venta Del Valle CDMX",
        "terreno venta Roma Condesa CDMX",
        "terreno venta Narvarte Nápoles CDMX",
        "terreno venta Juárez Cuauhtémoc CDMX",
        "terreno venta San Rafael Tabacalera CDMX",
        "terreno venta Anzures CDMX",
    ]

    for q in searches:
        try:
            url = (
                f"https://api.mercadolibre.com/sites/MLM/search"
                f"?q={requests.utils.quote(q)}"
                f"&category=MLM1473"
                f"&item_location=lat:19.20_19.60,lon:-99.35_-98.95"
                f"&limit=50"
            )
            r = requests.get(url, headers=auth_headers, timeout=15)
            if r.status_code != 200:
                print(f"    ML error {r.status_code}: {r.text[:80]}")
                continue

            data = r.json()
            items = data.get("results", [])
            print(f"    '{q[:30]}': {len(items)} resultados")

            for item in items:
                try:
                    title = item.get("title", "")
                    price = item.get("price")
                    link = item.get("permalink", "")
                    currency = item.get("currency_id", "MXN")
                    price_text = f"${price:,.0f} {currency}" if price else ""

                    area = None
                    frente = None
                    colonia = ""

                    for attr in item.get("attributes", []):
                        attr_id = attr.get("id", "")
                        val = attr.get("value_name", "") or ""
                        if attr_id in ("TOTAL_AREA", "LOT_SIZE"):
                            try: area = float(str(val).replace(",","").replace("m²","").strip())
                            except: pass
                        elif attr_id == "LOT_FRONTAGE":
                            try: frente = float(str(val).replace("m","").strip())
                            except: pass
                        elif attr_id == "NEIGHBORHOOD":
                            colonia = colonia_match(val) or val

                    if not colonia:
                        loc = item.get("location", {})
                        nb = loc.get("neighborhood", {}).get("name", "")
                        colonia = colonia_match(nb) or colonia_match(title)

                    if not colonia:
                        continue
                    if not passes_filters(area, frente):
                        continue

                    results.append(make_listing(
                        "MercadoLibre", title, price, price_text,
                        area, frente, link, colonia
                    ))
                except Exception:
                    continue

            time.sleep(0.5)

        except Exception as e:
            print(f"    Error: {e}")

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
                    colonia = colonia_match(nb) or colonia_match(title)
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

import requests
import time
import os

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "es-MX"}

MIN_M2 = 400
MAX_M2 = 1500
MIN_FRENTE = 14

COLONIAS_DISPLAY = [
    "Del Valle Norte", "Del Valle Centro", "Roma Norte", "Roma Sur",
    "Nápoles", "Cuauhtémoc", "Juárez", "Ciudad de los Deportes",
    "San Rafael", "Tabacalera", "Condesa", "Hipódromo",
    "Hipódromo Condesa", "Anzures"
]

# MercadoLibre category for land in CDMX
# MLM1473 = Terrenos y Lotes, state = Distrito Federal
ML_CATEGORY = "MLM1473"
ML_STATE = "TUxNREZFREVyYWwx"  # Distrito Federal

EASYBROKER_KEY = os.environ.get("EASYBROKER_API_KEY", "")


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
    """Basic filter: area in range, frente minimum."""
    if area and (area < MIN_M2 or area > MAX_M2):
        return False
    # Only reject on frente if we actually have the data
    if frente and frente < MIN_FRENTE:
        return False
    return True


def colonia_match(text):
    """Check if listing mentions one of our target colonias."""
    if not text:
        return ""
    text_lower = text.lower()
    for c in COLONIAS_DISPLAY:
        if c.lower() in text_lower:
            return c
        # partial matches
        parts = c.lower().split()
        if all(p in text_lower for p in parts):
            return c
    return ""


# ── MERCADOLIBRE API ──────────────────────────────────────────────────────────
def scrape_mercadolibre_api():
    results = []
    print("  [MercadoLibre API]")

    # Search terrenos in CDMX
    offset = 0
    while offset < 200:  # max 200 results per run
        url = (
            f"https://api.mercadolibre.com/sites/MLM/search"
            f"?category={ML_CATEGORY}"
            f"&state={ML_STATE}"
            f"&q=terreno+venta+CDMX"
            f"&offset={offset}&limit=50"
        )
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                print(f"    ML API error: {r.status_code}")
                break
            data = r.json()
            items = data.get("results", [])
            if not items:
                break

            for item in items:
                try:
                    title = item.get("title", "")
                    price = item.get("price")
                    link = item.get("permalink", "")
                    currency = item.get("currency_id", "MXN")
                    price_text = f"${price:,.0f} {currency}" if price else ""

                    # Extract area and frente from attributes
                    area = None
                    frente = None
                    colonia = ""
                    attrs = item.get("attributes", [])
                    for attr in attrs:
                        attr_id = attr.get("id", "")
                        val = attr.get("value_name", "") or ""
                        if attr_id == "TOTAL_AREA":
                            try: area = float(str(val).replace(",", "").replace("m²","").strip())
                            except: pass
                        elif attr_id == "LOT_FRONTAGE":
                            try: frente = float(str(val).replace("m","").strip())
                            except: pass
                        elif attr_id == "NEIGHBORHOOD":
                            colonia = val

                    # Try to match colonia from title if not in attributes
                    if not colonia:
                        colonia = colonia_match(title)
                    if not colonia:
                        loc = item.get("location", {})
                        neighborhood = loc.get("neighborhood", {}).get("name", "")
                        colonia = colonia_match(neighborhood) or neighborhood

                    # Filter: must be in our colonias
                    if not colonia:
                        continue

                    # Filter: area and frente
                    if not passes_filters(area, frente):
                        continue

                    listing = make_listing(
                        "MercadoLibre", title, price, price_text,
                        area, frente, link, colonia
                    )
                    results.append(listing)

                except Exception as e:
                    continue

            offset += 50
            if offset < data.get("paging", {}).get("total", 0):
                time.sleep(1)
            else:
                break

        except Exception as e:
            print(f"    ML error: {e}")
            break

    print(f"    ✓ {len(results)} terrenos encontrados")
    return results


# ── EASYBROKER API ────────────────────────────────────────────────────────────
def scrape_easybroker_api():
    results = []
    if not EASYBROKER_KEY:
        print("  [EasyBroker] Sin API key — skip")
        return results

    print("  [EasyBroker API]")
    page = 1
    while page <= 5:
        url = (
            f"https://api.easybroker.com/v1/properties"
            f"?operation_type=sale&property_type=land"
            f"&location=Ciudad+de+Mexico"
            f"&page={page}&per_page=50"
        )
        try:
            r = requests.get(url, headers={
                **HEADERS,
                "X-Authorization": EASYBROKER_KEY
            }, timeout=15)
            if r.status_code != 200:
                print(f"    EB error: {r.status_code}")
                break
            data = r.json()
            items = data.get("content", [])
            if not items:
                break

            for item in items:
                try:
                    title = item.get("title", "Terreno")
                    price = item.get("asking_price")
                    price_text = f"${price:,.0f} MXN" if price else ""
                    link = item.get("public_url", "")
                    area = item.get("lot_size") or item.get("construction_size")
                    location = item.get("location", {})
                    neighborhood = location.get("neighborhood", "") or ""
                    colonia = colonia_match(neighborhood) or colonia_match(title)

                    if not colonia:
                        continue
                    if not passes_filters(area, None):
                        continue

                    listing = make_listing(
                        "EasyBroker", title, price, price_text,
                        area, None, link, colonia
                    )
                    results.append(listing)
                except Exception:
                    continue

            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"    EB error: {e}")
            break

    print(f"    ✓ {len(results)} terrenos encontrados")
    return results


# ── MASTER ────────────────────────────────────────────────────────────────────
def scrape_all():
    all_results = []
    all_results.extend(scrape_mercadolibre_api())
    all_results.extend(scrape_easybroker_api())
    print(f"\n  Total: {len(all_results)} terrenos que cumplen filtros")
    return all_results

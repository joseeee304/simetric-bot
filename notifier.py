import requests
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

PORTALES = ["Inmuebles24","Vivanuncios","Lamudi","MercadoLibre",
            "Propiedades.com","MetrosCúbicos","EasyBroker","Century21",
            "RE/MAX","Coldwell Banker","OLX","ERA"]

def format_price(price):
    if not price: return "Precio no especificado"
    if price >= 1_000_000: return f"${price/1_000_000:.1f}M MXN"
    return f"${price:,.0f} MXN"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] Sin credenciales")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": False}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[telegram] Error: {e}")
        return False

def notify_new_listing(listing):
    area_str = f"{listing['area']:.0f} m²" if listing.get("area") else listing.get("area_text","m² no esp.")
    msg = (
        f"🏗️ <b>NUEVO TERRENO — {listing['colonia']}</b>\n\n"
        f"📐 <b>Superficie:</b> {area_str}\n"
        f"💰 <b>Precio:</b> {format_price(listing.get('price'))}\n"
        f"🏪 <b>Portal:</b> {listing['portal']}\n"
        f"📋 <b>Título:</b> {listing['title'][:80]}\n\n"
        f"🔗 <a href=\"{listing['link']}\">Ver en {listing['portal']}</a>"
    )
    return send_telegram(msg)

def notify_summary(new_count, total_scanned):
    if new_count == 0:
        msg = f"🔍 <b>Simetric Bot — Sin novedades</b>\n\nRevisé {total_scanned} anuncios en {len(PORTALES)} portales.\nNo hay terrenos nuevos."
    else:
        msg = f"✅ <b>Simetric Bot — {new_count} terreno(s) nuevo(s)</b>\n\nRevisé {total_scanned} anuncios en {len(PORTALES)} portales."
    send_telegram(msg)

def notify_startup():
    portales_str = "\n".join(f"• {p}" for p in PORTALES)
    msg = (
        f"🤖 <b>Simetric Terrenos Bot v2 — Activo</b>\n\n"
        f"Revisando cada 6 horas en <b>{len(PORTALES)} portales</b>:\n"
        f"{portales_str}\n\n"
        f"Filtros:\n📐 400–1,500 m²  📏 Mín. 14m frente\n📍 14 colonias CDMX"
    )
    send_telegram(msg)

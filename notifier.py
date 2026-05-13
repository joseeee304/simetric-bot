import requests
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def fmt_price(price):
    if not price: return "Precio no especificado"
    if price >= 1_000_000: return f"${price/1_000_000:.1f}M MXN"
    return f"${price:,.0f} MXN"


def send(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TG] {msg[:80]}")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[TG error] {e}")
        return False


def notify_listing(l):
    area = f"{l['area']:.0f} m²" if l.get("area") else "m² no especificado"
    frente = f"{l['frente']}m de frente" if l.get("frente") else ""
    frente_str = f"\n📏 <b>Frente:</b> {frente}" if frente else ""

    msg = (
        f"🏗️ <b>TERRENO — {l['colonia']}</b>\n\n"
        f"📐 <b>Superficie:</b> {area}{frente_str}\n"
        f"💰 <b>Precio:</b> {fmt_price(l.get('price'))}\n"
        f"🏪 <b>Portal:</b> {l['portal']}\n"
        f"📋 {l['title'][:80]}\n\n"
        f"🔗 <a href=\"{l['link']}\">Ver anuncio</a>"
    )
    return send(msg)


def notify_summary(new_count, total):
    if new_count == 0:
        send(f"🔍 <b>Scan completo</b> — Sin terrenos nuevos\n{total} revisados en MercadoLibre y EasyBroker.")
    else:
        send(f"✅ <b>{new_count} terreno(s) nuevo(s)</b> encontrados de {total} revisados.")


def notify_startup():
    send(
        "🤖 <b>Simetric Terrenos Bot — Activo</b>\n\n"
        "Revisando cada 6h:\n"
        "• MercadoLibre (API oficial)\n"
        "• EasyBroker (API oficial)\n\n"
        "Filtros:\n"
        "📐 400–1,500 m²\n"
        "📏 Mín. 14m frente\n"
        "📍 14 colonias CDMX\n"
        "🔁 Sin repetir anuncios ya vistos"
    )

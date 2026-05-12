import requests
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MAX_ALERTS_PER_SCAN = 2  # max new alerts per scan cycle
SCORE_ALERT_MIN = 5      # minimum score to alert immediately


def fmt_price(price):
    if not price: return "Precio no especificado"
    if price >= 1_000_000: return f"${price/1_000_000:.1f}M MXN"
    return f"${price:,.0f} MXN"


def fmt_score(score):
    if score >= 8: return f"🔥 {score}/10"
    if score >= 5: return f"📍 {score}/10"
    return f"⚪ {score}/10"


def send(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[telegram] {message[:80]}")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[telegram] error: {e}")
        return False


def notify_new(listing, score):
    area_str = f"{listing['area']:.0f} m²" if listing.get("area") else listing.get("area_text", "—")
    frente_str = f"{listing['frente']}m" if listing.get("frente") else "—"
    emoji = "🚨" if score >= 8 else "📍"

    msg = (
        f"{emoji} <b>TERRENO NUEVO — {listing['colonia']}</b>  {fmt_score(score)}\n\n"
        f"📐 <b>Superficie:</b> {area_str}   <b>Frente:</b> {frente_str}\n"
        f"💰 <b>Precio:</b> {fmt_price(listing.get('price'))}\n"
        f"🏪 <b>Portal:</b> {listing['portal']}\n"
        f"📋 {listing['title'][:70]}\n\n"
        f"🔗 <a href=\"{listing['link']}\">Ver anuncio</a>"
    )
    return send(msg)


def notify_price_drop(listing, old_price, score):
    diff = old_price - (listing.get("price") or 0)
    pct = (diff / old_price * 100) if old_price else 0
    msg = (
        f"📉 <b>BAJÓ DE PRECIO — {listing['colonia']}</b>  {fmt_score(score)}\n\n"
        f"💰 <b>Antes:</b> {fmt_price(old_price)}\n"
        f"💰 <b>Ahora:</b> {fmt_price(listing.get('price'))}\n"
        f"✂️ <b>Bajó:</b> {fmt_price(diff)} ({pct:.1f}%)\n\n"
        f"🔗 <a href=\"{listing['link']}\">Ver anuncio</a>"
    )
    return send(msg)


def notify_digest(listings):
    if not listings:
        return
    now = datetime.utcnow().strftime("%d/%m/%Y")
    lines = [f"☀️ <b>Resumen diario Simetric — {now}</b>\n"]
    for i, l in enumerate(listings[:5], 1):
        area_str = f"{l['area']:.0f}m²" if l.get("area") else "—"
        lines.append(
            f"{i}. <b>{l['colonia']}</b> · {area_str} · {fmt_price(l.get('price'))} · {fmt_score(l.get('score',0))}\n"
            f"   <a href=\"{l['link']}\">{l['portal']}</a>"
        )
    send("\n".join(lines))


def notify_summary(new_count, price_drops, skipped, total_scanned):
    if new_count == 0 and price_drops == 0:
        msg = (f"🔍 <b>Scan completo — Sin novedades</b>\n\n"
               f"Revisé {total_scanned} anuncios en 12 portales.\n"
               f"{skipped} no pasaron el score mínimo.")
    else:
        parts = []
        if new_count: parts.append(f"{new_count} terreno(s) nuevo(s)")
        if price_drops: parts.append(f"{price_drops} bajada(s) de precio")
        msg = (f"✅ <b>Scan completo — {' · '.join(parts)}</b>\n\n"
               f"Revisé {total_scanned} anuncios · {skipped} descartados por score bajo.")
    send(msg)


def notify_startup():
    send(
        "🤖 <b>Simetric Terrenos Bot v3 — Activo</b>\n\n"
        "✦ 12 portales · 14 colonias · cada 6h\n"
        "✦ Score de oportunidad 1-10\n"
        "✦ Deduplicación cross-portal\n"
        "✦ Alertas de bajada de precio\n"
        "✦ Digest diario a las 8am\n\n"
        "Filtros: 400–1,500 m²  ·  Mín. 14m frente"
    )

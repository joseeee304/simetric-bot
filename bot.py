import schedule
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scraper import scrape_all
from notifier import (notify_new, notify_price_drop, notify_digest,
                      notify_summary, notify_startup)
from storage import init_db, process_listing, mark_alerted, get_daily_digest

MAX_ALERTS_PER_SCAN = 2
SCORE_MIN = 5


def run_scan():
    print(f"\n🔍 Scan iniciado — {datetime.utcnow().strftime('%H:%M %d/%m/%Y')}")
    alerts_sent = 0
    price_drops = 0
    skipped = 0
    top_candidates = []  # score >= SCORE_MIN but over alert limit

    try:
        listings = scrape_all()
        print(f"  Total encontrados: {len(listings)}")

        # Sort by score potential first (deduplicated in storage)
        for listing in listings:
            (status, existing), fp, score = process_listing(listing)

            # Skip low score
            if score < SCORE_MIN:
                skipped += 1
                continue

            # Price drop detection
            if status == "updated" and existing:
                old_price = existing.get("price") or 0
                new_price = listing.get("price") or 0
                if old_price and new_price and (old_price - new_price) > old_price * 0.05:
                    print(f"  📉 BAJÓ PRECIO: {listing['colonia']} {old_price}→{new_price}")
                    notify_price_drop(listing, old_price, score)
                    mark_alerted(fp)
                    price_drops += 1
                continue

            # New listing — check alert limit
            if status == "new":
                if alerts_sent < MAX_ALERTS_PER_SCAN:
                    print(f"  ✅ NUEVO (score {score}): {listing['colonia']} — {listing.get('area_text')} — {listing.get('price_text')}")
                    notify_new(listing, score)
                    mark_alerted(fp)
                    alerts_sent += 1
                else:
                    top_candidates.append((score, listing, fp))

        # Save non-alerted candidates for digest
        for score, listing, fp in sorted(top_candidates, reverse=True)[:10]:
            print(f"  💾 Guardado sin alertar (score {score}): {listing['colonia']}")

        notify_summary(alerts_sent, price_drops, skipped, len(listings))
        print(f"✅ Scan completo — {alerts_sent} alertas, {price_drops} bajadas, {skipped} descartados\n")

    except Exception as e:
        print(f"❌ Error en scan: {e}")
        import traceback
        traceback.print_exc()


def run_daily_digest():
    print("☀️ Enviando digest diario...")
    try:
        top = get_daily_digest()
        if top:
            notify_digest(top)
            print(f"  Digest enviado con {len(top)} terrenos")
        else:
            print("  Sin terrenos para el digest")
    except Exception as e:
        print(f"❌ Error en digest: {e}")


def main():
    print("🤖 Simetric Terrenos Bot v3 iniciando...")
    init_db()
    notify_startup()

    # First scan immediately
    run_scan()

    # Schedule scans every 6 hours
    schedule.every(6).hours.do(run_scan)

    # Daily digest at 8am Mexico City time (UTC-6 = 14:00 UTC)
    schedule.every().day.at("14:00").do(run_daily_digest)

    print("⏰ Programado: scan cada 6h · digest diario 8am CDMX")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()

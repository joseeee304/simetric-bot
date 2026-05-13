import schedule
import time
import sys
import os
from datetime import datetime

# Files are in the same directory as bot.py
sys.path.insert(0, os.path.dirname(__file__))

from scraper import scrape_all
from notifier import notify_listing, notify_summary, notify_startup
from storage import get_new, mark_seen


def run_scan():
    print(f"\n🔍 Scan — {datetime.utcnow().strftime('%H:%M %d/%m/%Y')}")
    try:
        listings = scrape_all()
        new_listings, seen, data = get_new(listings)
        print(f"  Nuevos: {len(new_listings)} de {len(listings)} totales")

        for l in new_listings:
            print(f"  → {l['colonia']} | {l.get('area')} m² | {l.get('price_text')}")
            notify_listing(l)
            time.sleep(1.5)

        mark_seen(new_listings, seen, data)
        notify_summary(len(new_listings), len(listings))

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback; traceback.print_exc()


def main():
    print("🤖 Simetric Bot v4 iniciando...")
    notify_startup()
    run_scan()
    schedule.every(6).hours.do(run_scan)
    print("⏰ Scan cada 6 horas.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()

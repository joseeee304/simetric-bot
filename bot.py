import schedule
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from scraper import scrape_all
from notifier import notify_new_listing, notify_summary, notify_startup
from storage import get_new_listings, mark_as_seen


def run_scan():
    print("\n🔍 Iniciando scan de terrenos...")
    
    try:
        all_listings = scrape_all()
        print(f"   Total encontrados: {len(all_listings)}")

        new_listings, seen = get_new_listings(all_listings)
        print(f"   Nuevos: {len(new_listings)}")

        for listing in new_listings:
            print(f"   ✅ NUEVO: {listing['colonia']} — {listing['area_text']} — {listing['price_text']}")
            notify_new_listing(listing)
            time.sleep(1)

        mark_as_seen(all_listings, seen)
        notify_summary(len(new_listings), len(all_listings))
        print(f"✅ Scan completo. {len(new_listings)} nuevos de {len(all_listings)} totales.\n")

    except Exception as e:
        print(f"❌ Error en scan: {e}")


def main():
    print("🤖 Simetric Terrenos Bot iniciando...")
    notify_startup()

    # Run immediately on start
    run_scan()

    # Then every 6 hours
    schedule.every(6).hours.do(run_scan)

    print("⏰ Programado cada 6 horas. Esperando...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()

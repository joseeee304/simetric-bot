import json
import os

DB_FILE = os.environ.get("DB_PATH", "/app/data/seen_listings.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def load_seen():
    _ensure_dir()
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("ids", []))
    except Exception:
        return set()


def save_seen(seen_ids):
    _ensure_dir()
    with open(DB_FILE, "w") as f:
        json.dump({"ids": list(seen_ids)}, f)


def get_new_listings(listings):
    seen = load_seen()
    new = [l for l in listings if l["id"] not in seen]
    return new, seen


def mark_as_seen(listings, existing_seen):
    new_ids = {l["id"] for l in listings}
    updated = existing_seen | new_ids
    # Keep only last 2000 to avoid file growing forever
    if len(updated) > 2000:
        updated = set(list(updated)[-2000:])
    save_seen(updated)

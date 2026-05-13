import json
import os
from datetime import datetime

JSON_PATH = os.environ.get("DB_PATH", "/app/data/seen.json")


def _load():
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    if not os.path.exists(JSON_PATH):
        return {"seen": [], "listings": {}}
    try:
        with open(JSON_PATH) as f:
            return json.load(f)
    except:
        return {"seen": [], "listings": {}}


def _save(data):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, default=str, indent=2)


def get_new(listings):
    """Return only listings not seen before."""
    data = _load()
    seen = set(data.get("seen", []))
    new = [l for l in listings if l["id"] not in seen]
    return new, seen, data


def mark_seen(new_listings, seen, data):
    """Save new listings as seen."""
    for l in new_listings:
        seen.add(l["id"])
        data["listings"][l["id"]] = {
            **l,
            "first_seen": datetime.utcnow().isoformat()
        }
    # Keep only last 5000
    seen_list = list(seen)
    if len(seen_list) > 5000:
        seen_list = seen_list[-5000:]
    data["seen"] = seen_list
    _save(data)

import os
import json
import hashlib
from datetime import datetime, timedelta

# Try PostgreSQL, fall back to JSON
try:
    import psycopg2
    import psycopg2.extras
    HAS_PG = bool(os.environ.get("DATABASE_URL"))
except ImportError:
    HAS_PG = False

DB_URL = os.environ.get("DATABASE_URL", "")
JSON_PATH = os.environ.get("DB_PATH", "/app/data/listings.json")

BENCHMARKS = {
    "Del Valle Norte":    65000, "Del Valle Centro":   68000,
    "Roma Norte":         90000, "Roma Sur":           80000,
    "Nápoles":            60000, "Cuauhtémoc":         55000,
    "Juárez":             85000, "Cd. de los Deportes":55000,
    "San Rafael":         60000, "Tabacalera":         55000,
    "Condesa":           100000, "Hipódromo":          90000,
    "Hipódromo Condesa":  95000, "Anzures":            80000,
}


# ── Fingerprint for deduplication ────────────────────────────────────────────
def make_fingerprint(listing):
    colonia = listing.get("colonia", "")
    area = round((listing.get("area") or 0) / 10) * 10      # round to 10m²
    price = round((listing.get("price") or 0) / 50000) * 50000  # round to 50k
    raw = f"{colonia}|{area}|{price}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── Score algorithm ───────────────────────────────────────────────────────────
def score_listing(listing):
    score = 0
    colonia = listing.get("colonia", "")
    price = listing.get("price") or 0
    area = listing.get("area") or 0
    frente = listing.get("frente") or 0
    desc = (listing.get("title") or "").lower()

    # Price per m² vs benchmark
    if area > 0 and price > 0:
        ppm2 = price / area
        bench = BENCHMARKS.get(colonia, 70000)
        if ppm2 < bench * 0.80:   score += 3
        elif ppm2 < bench * 0.90: score += 2
        elif ppm2 < bench * 0.97: score += 1

    # Frente
    if frente >= 20:   score += 2
    elif frente >= 15: score += 1

    # Keywords positivos
    for kw in ["escrituras", "uso habitacional", "uso de suelo", "esquina", "demoler"]:
        if kw in desc: score += 1

    # Has both price and area = complete listing
    if price > 0 and area > 0: score += 1

    return min(score, 10)


# ── PostgreSQL backend ────────────────────────────────────────────────────────
def pg_connect():
    return psycopg2.connect(DB_URL)


def pg_init():
    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT,
                    portal TEXT,
                    colonia TEXT,
                    title TEXT,
                    price BIGINT,
                    price_text TEXT,
                    area FLOAT,
                    area_text TEXT,
                    frente FLOAT,
                    score INT DEFAULT 0,
                    link TEXT,
                    first_seen TIMESTAMP DEFAULT NOW(),
                    last_seen TIMESTAMP DEFAULT NOW(),
                    price_history JSONB DEFAULT '[]'::jsonb,
                    alerted BOOLEAN DEFAULT FALSE
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint ON listings(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_colonia ON listings(colonia)")
        conn.commit()


def pg_get_existing(fingerprints):
    if not fingerprints:
        return {}
    with pg_connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM listings WHERE fingerprint = ANY(%s)", (list(fingerprints),))
            return {row["fingerprint"]: dict(row) for row in cur.fetchall()}


def pg_upsert(listing, fp, score):
    now = datetime.utcnow()
    with pg_connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, price, price_history, alerted FROM listings WHERE fingerprint=%s", (fp,))
            existing = cur.fetchone()
            if existing:
                # Update price history if changed
                price_history = existing["price_history"] or []
                if existing["price"] and listing.get("price") and abs(existing["price"] - listing["price"]) > 10000:
                    price_history.append({"price": existing["price"], "date": now.isoformat()})
                cur.execute("""
                    UPDATE listings SET last_seen=%s, price=%s, price_text=%s,
                    score=%s, price_history=%s WHERE fingerprint=%s
                """, (now, listing.get("price"), listing.get("price_text"),
                      score, json.dumps(price_history), fp))
                conn.commit()
                return "updated", existing
            else:
                cur.execute("""
                    INSERT INTO listings (id, fingerprint, portal, colonia, title, price, price_text,
                    area, area_text, frente, score, link, first_seen, last_seen, alerted)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (listing["id"], fp, listing.get("portal"), listing.get("colonia"),
                      listing.get("title"), listing.get("price"), listing.get("price_text"),
                      listing.get("area"), listing.get("area_text"), listing.get("frente"),
                      score, listing.get("link"), now, now, False))
                conn.commit()
                return "new", None


def pg_mark_alerted(fingerprint):
    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE listings SET alerted=TRUE WHERE fingerprint=%s", (fingerprint,))
        conn.commit()


def pg_get_daily_digest():
    yesterday = datetime.utcnow() - timedelta(hours=24)
    with pg_connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM listings
                WHERE first_seen >= %s AND score >= 5
                ORDER BY score DESC LIMIT 5
            """, (yesterday,))
            return [dict(r) for r in cur.fetchall()]


# ── JSON fallback backend ─────────────────────────────────────────────────────
def _load_json():
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    if not os.path.exists(JSON_PATH):
        return {"listings": {}}
    try:
        with open(JSON_PATH) as f:
            return json.load(f)
    except:
        return {"listings": {}}


def _save_json(data):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, default=str)


def json_upsert(listing, fp, score):
    data = _load_json()
    listings = data.get("listings", {})
    now = datetime.utcnow().isoformat()
    existing = listings.get(fp)
    if existing:
        price_history = existing.get("price_history", [])
        if existing.get("price") and listing.get("price") and abs(existing["price"] - listing["price"]) > 10000:
            price_history.append({"price": existing["price"], "date": now})
        existing.update({"last_seen": now, "price": listing.get("price"),
                         "price_text": listing.get("price_text"),
                         "score": score, "price_history": price_history})
        listings[fp] = existing
        _save_json(data)
        return "updated", existing
    else:
        listings[fp] = {**listing, "fingerprint": fp, "score": score,
                        "first_seen": now, "last_seen": now,
                        "alerted": False, "price_history": []}
        # Keep only last 3000
        if len(listings) > 3000:
            sorted_keys = sorted(listings, key=lambda k: listings[k].get("last_seen", ""))
            for old in sorted_keys[:500]:
                del listings[old]
        data["listings"] = listings
        _save_json(data)
        return "new", None


def json_mark_alerted(fp):
    data = _load_json()
    if fp in data.get("listings", {}):
        data["listings"][fp]["alerted"] = True
        _save_json(data)


def json_get_daily_digest():
    data = _load_json()
    yesterday = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    results = [v for v in data.get("listings", {}).values()
               if v.get("first_seen", "") >= yesterday and v.get("score", 0) >= 5]
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:5]


# ── Public API ────────────────────────────────────────────────────────────────
def init_db():
    if HAS_PG and DB_URL:
        pg_init()
        print("  [db] PostgreSQL inicializado")
    else:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        print("  [db] JSON storage inicializado")


def process_listing(listing):
    fp = make_fingerprint(listing)
    score = score_listing(listing)
    if HAS_PG and DB_URL:
        return pg_upsert(listing, fp, score), fp, score
    else:
        return json_upsert(listing, fp, score), fp, score


def mark_alerted(fp):
    if HAS_PG and DB_URL:
        pg_mark_alerted(fp)
    else:
        json_mark_alerted(fp)


def get_daily_digest():
    if HAS_PG and DB_URL:
        return pg_get_daily_digest()
    else:
        return json_get_daily_digest()

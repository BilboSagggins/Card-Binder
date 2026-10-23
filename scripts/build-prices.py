#!/usr/bin/env python3
"""Build compact TCGplayer price lists for the binder app from TCGCSV (https://tcgcsv.com).

TCGCSV republishes TCGplayer's catalog and market prices once a day. Browsers can't read it
directly, so this script (run daily by .github/workflows/prices.yml) copies the parts the app
needs into prices/<game>.json on the site (pokemon, pokemon-jp, onepiece):

  { "updated": "...", "groups": { "<groupId>": "<set name>" },
    "sets": [[groupId, "<set name>", "<release date YYYY-MM-DD>", "<abbreviation>", <card count>], ...],
    "p": { "<productId>": [marketPrice, "name", "number", groupId, "rarity"] } }

Only single cards (products with a card Number) are kept.
"""
import json, os, re, sys, time, urllib.request

BASE = os.environ.get("TCGCSV_BASE", "https://tcgcsv.com/tcgplayer")
GAMES = {"pokemon": [3], "pokemon-jp": [85], "onepiece": [68]}   # 85 = Pokemon Japan (its own file, loaded only for Japanese cards)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prices")
# which price to use when a product has several printings listed
PREFER = ["Holofoil", "Normal", "Foil", "Reverse Holofoil", "1st Edition Holofoil", "1st Edition", "Unlimited Holofoil", "Unlimited"]


def get(path, tries=4):
    url = f"{BASE}/{path}"
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "card-binder-price-sync (github.com/BilboSagggins/Card-Binder)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            return data.get("results") or []
        except Exception as e:  # network hiccup: wait and retry
            if n == tries - 1:
                print(f"  ! gave up on {path}: {e}", file=sys.stderr)
                return []
            time.sleep(2 + 3 * n)


def pick_price(rows):
    by = {r.get("subTypeName") or "": r for r in rows}
    order = PREFER + [k for k in by if k not in PREFER]
    for key in order:
        r = by.get(key)
        if r and r.get("marketPrice") is not None:
            return round(float(r["marketPrice"]), 2)
    for key in order:  # no market price: fall back to the middle listing price
        r = by.get(key)
        if r and r.get("midPrice") is not None:
            return round(float(r["midPrice"]), 2)
    return None


def build(game, cats):
    """Single cards into one list, sealed product into a second (prices/<game>-sealed.json)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = {"updated": now, "groups": {}, "sets": [], "p": {}}
    sealed = {"updated": now, "groups": {}, "sets": [], "p": {}}
    for cat in cats:
        add_category(game, cat, out, sealed)
    SEALED[game] = sealed
    return out


SEALED = {}
CURRENT = {}   # productId -> today's price (cards and sealed), for the 7-day spike check
# Details only single cards have
CARD_FIELDS = ("Rarity", "Card Type", "CardType", "HP", "Stage", "Attack 1", "Card Text", "Weakness", "Resistance", "Retreat Cost", "Cost", "Power", "Counterplus", "Color", "Life")
# Not sealed product, even though they have no card number
NOT_SEALED = re.compile(r"code card|online code|digital|\bpromo card\b|playmat|sleeves|deck box|binder|portfolio|card case|dice|coin\b|damage counter|figure|plush|pin\b|poster|art print|oversized|jumbo|\bmat\b", re.I)
# What kind of sealed product it is, from its name (first match wins)
SEALED_TYPES = [
    ("Case", r"\bcase\b"),
    ("Booster Box", r"booster box|booster display|display box|\bbooster  ?display"),
    ("Elite Trainer Box", r"elite trainer box|\betb\b"),
    ("Booster Bundle", r"booster bundle|bundle"),
    ("Build & Battle", r"build (&|and) battle|prerelease kit|prerelease pack"),
    ("Ultra Premium Collection", r"ultra.premium|super.premium"),
    ("Premium Collection", r"premium collection|premium figure|special collection|figure collection"),
    ("Tin", r"\btins?\b|mini tin|stacking tin"),
    ("Blister", r"blister|checklane|3.pack|three.pack|2.pack|two.pack|sleeved booster|booster pack.*art|poke ball tin"),
    ("Deck", r"\bdecks?\b|theme deck|battle deck|league battle|starter set|trainer kit|battle academy|v battle|ex battle"),
    ("Booster Pack", r"booster pack|\bbooster\b|\bpack\b"),
    ("Collection / Box", r"collection|\bbox\b|chest|gift set|calendar|showcase|toolkit|special set|card set|file set|premium file|\bkit\b|commemoration|briefcase|don!! set"),
]
SEALED_TYPES = [(t, re.compile(rx, re.I)) for t, rx in SEALED_TYPES]


def sealed_type(name):
    for t, rx in SEALED_TYPES:
        if rx.search(name):
            return t
    return "Other"


def add_category(game, cat, out, sealed):
    groups = get(f"{cat}/groups")
    for i, g in enumerate(groups, 1):
        gid = g["groupId"]
        products = get(f"{cat}/{gid}/products")
        if not products:
            continue
        prices = {}
        for r in get(f"{cat}/{gid}/prices"):
            prices.setdefault(r["productId"], []).append(r)
        kept = kept_sealed = 0
        for p in products:
            ext = {e.get("name"): e.get("value") for e in (p.get("extendedData") or [])}
            number = (ext.get("Number") or "").strip()
            if not number:  # sealed product, not a single card
                name = (p.get("name") or "").strip()
                if any((ext.get(k) or "").strip() for k in CARD_FIELDS):  # a single card without a number, not a product
                    continue
                if name and not NOT_SEALED.search(name):
                    sealed["p"][str(p["productId"])] = [pick_price(prices.get(p["productId"], [])), name, gid, sealed_type(name)]
                    CURRENT[str(p["productId"])] = sealed["p"][str(p["productId"])][0]
                    kept_sealed += 1
                continue
            name = p.get("name") or ""
            if name.endswith(" - " + number):
                name = name[: -len(" - " + number)]
            out["p"][str(p["productId"])] = [pick_price(prices.get(p["productId"], [])), name, number, gid, (ext.get("Rarity") or "").strip()]
            CURRENT[str(p["productId"])] = out["p"][str(p["productId"])][0]
            kept += 1
        if kept_sealed:
            sealed["groups"][str(gid)] = g.get("name") or ""
            sealed["sets"].append([gid, g.get("name") or "", (g.get("publishedOn") or "")[:10], g.get("abbreviation") or "", kept_sealed])
        if kept:
            out["groups"][str(gid)] = g.get("name") or ""
            out["sets"].append([gid, g.get("name") or "", (g.get("publishedOn") or "")[:10], g.get("abbreviation") or "", kept])
        if i % 25 == 0:
            print(f"  {game} (category {cat}): {i}/{len(groups)} sets", flush=True)
        time.sleep(0.15)  # be gentle with a free service


# --- Chinese Pokémon from CardTrader (TCGplayer has none). Needs the CARDTRADER_TOKEN secret; skipped without it.
#     prices/pokemon-zh.json: same shape, but keys are CardTrader card ids, prices are the lowest current
#     Chinese-language listing in USD, and each entry adds a picture path: [price, name, number, setId, rarity, image]
CT = "https://api.cardtrader.com/api/v2"
CT_IMG = "/uploads/blueprints/image/"


def ct_get(path, token, tries=4):
    for n in range(tries):
        try:
            req = urllib.request.Request(f"{CT}/{path}", headers={"Authorization": f"Bearer {token}", "User-Agent": "card-binder-price-sync"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            code = getattr(e, "code", None)
            if code in (401, 403, 404):
                print(f"  CardTrader {path.split('?')[0]}: HTTP {code}", file=sys.stderr); return None
            time.sleep(3 + 4 * n)
    print(f"  CardTrader {path.split('?')[0]}: gave up", file=sys.stderr)
    return None


def is_chinese_set(e):
    code, name = (e.get("code") or "").lower(), e.get("name") or ""
    return (e.get("id") or 0) >= 3900 and (re.match(r"(m-)?c[sb]", code) or re.search(r"chinese", name, re.I))


def build_cardtrader():
    token = os.environ.get("CARDTRADER_TOKEN", "").strip()
    if not token:
        print("  no CARDTRADER_TOKEN; skipping Chinese cards", flush=True); return None
    exps = [e for e in (ct_get("expansions", token) or []) if e.get("game_id") == 5 and is_chinese_set(e)]
    out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "cardtrader", "currency": "USD", "groups": {}, "sets": [], "p": {}}
    for e in sorted(exps, key=lambda e: e["id"]):
        eid = e["id"]
        bps = [b for b in (ct_get(f"blueprints/export?expansion_id={eid}", token) or []) if b.get("category_id") == 73]
        if not bps:
            continue
        time.sleep(1.1)  # the marketplace endpoint allows about one call a second
        prods = ct_get(f"marketplace/products?expansion_id={eid}", token) or {}
        for b in bps:
            fp = b.get("fixed_properties") or {}
            listings = [x for x in prods.get(str(b["id"]), []) if str((x.get("properties_hash") or {}).get("pokemon_language") or "").startswith("zh") and not x.get("graded")]
            nm = [x for x in listings if (x.get("properties_hash") or {}).get("condition") in ("Mint", "Near Mint")] or listings
            cents = min(((x.get("price") or {}).get("cents") or x.get("price_cents") or 0 for x in nm), default=0)
            ver = [v.strip() for v in str(b.get("version") or "").split("|")]
            number = ver[-1] if len(ver) > 1 and "/" in ver[-1] else str(fp.get("collector_number") or "")
            img = ((b.get("image") or {}).get("url") or "").replace(CT_IMG, "")
            rarity = {"Special Illustration": "Special Illustration Rare"}.get(fp.get("pokemon_rarity") or "", fp.get("pokemon_rarity") or "")
            out["p"][str(b["id"])] = [round(cents / 100, 2) if cents else None, b.get("name") or "", number, eid, rarity, img]
        out["groups"][str(eid)] = e.get("name") or ""
        out["sets"].append([eid, e.get("name") or "", "", e.get("code") or "", len(bps)])
        print(f"  {e.get('name')}: {len(bps)} cards", flush=True)
    return out


# --- 7-day price spikes: compare today's prices with TCGCSV's daily archive from a week ago
#     prices/spikes.json = { updated, from: "YYYY-MM-DD", rise: 0.2, p: { productId: [price then, price now] } }
SPIKE = 0.20


SPIKE_LOG = []


def slog(msg):
    SPIKE_LOG.append(msg); print("  " + msg, flush=True)


HIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".price-history")   # kept in the Actions cache, not in the repo


def baseline_from_history(today):
    """Prices from our own daily snapshots, 7 to 9 days back."""
    import datetime
    for back in (7, 8, 9):
        day = (today - datetime.timedelta(days=back)).isoformat()
        path = os.path.join(HIST, day + ".json")
        if os.path.exists(path):
            try:
                return day, json.load(open(path))
            except Exception as e:
                slog(f"history {day}: unreadable ({e})")
    return None, None


def baseline_from_archive(today):
    """TCGCSV's daily archive from a week ago (may be refused from GitHub's servers)."""
    import datetime, glob, shutil, subprocess, tempfile
    tool = shutil.which("7z") or shutil.which("7zz") or shutil.which("7za")
    if not tool:
        slog("no 7z tool for the archive"); return None, None
    cats = sorted({c for cs in GAMES.values() for c in cs})
    for back in (7, 8):
        day = (today - datetime.timedelta(days=back)).isoformat()
        work = tempfile.mkdtemp(); arc = os.path.join(work, "prices.7z")
        r = subprocess.run(["curl", "-fsSL", "--max-time", "300", "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                            "-o", arc, f"https://tcgcsv.com/archive/tcgplayer/prices-{day}.ppmd.7z"], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(arc):
            slog(f"archive {day}: download failed ({r.returncode}: {r.stderr.strip()[-120:]})"); shutil.rmtree(work, ignore_errors=True); continue
        subprocess.run([tool, "x", "-y", f"-o{work}", arc] + [f"{day}/{c}/*" for c in cats], check=False, capture_output=True)
        then = {}
        for path in glob.glob(os.path.join(work, day, "*", "*", "prices")):
            try:
                rows = json.load(open(path)).get("results") or []
            except Exception:
                continue
            by = {}
            for x in rows:
                by.setdefault(x["productId"], []).append(x)
            for pid, rs in by.items():
                then[str(pid)] = pick_price(rs)
        shutil.rmtree(work, ignore_errors=True)
        slog(f"archive {day}: {len(then)} prices")
        if len(then) >= 1000:
            return day, then
    return None, None


def build_spikes():
    import datetime
    today = datetime.datetime.now(datetime.timezone.utc).date()
    # remember today's prices for next week's comparison, and forget snapshots older than two weeks
    os.makedirs(HIST, exist_ok=True)
    with open(os.path.join(HIST, today.isoformat() + ".json"), "w") as f:
        json.dump({k: v for k, v in CURRENT.items() if v is not None}, f, separators=(",", ":"))
    for name in os.listdir(HIST):
        if name.endswith(".json") and name[:10] < (today - datetime.timedelta(days=14)).isoformat():
            os.remove(os.path.join(HIST, name))
    slog(f"history: {sorted(n[:10] for n in os.listdir(HIST))}")
    day, then = baseline_from_history(today)
    if not then:
        day, then = baseline_from_archive(today)
    if not then:
        slog("no prices from a week ago yet; spikes start once a week of history is saved"); return None
    spikes = {pid: [old, CURRENT[pid]] for pid, old in then.items()
              if old and old > 0 and CURRENT.get(pid) is not None and CURRENT[pid] >= old * (1 + SPIKE)}
    slog(f"{len(spikes)} products up {int(SPIKE * 100)}%+ since {day} (of {len(then)} compared, {len(CURRENT)} today)")
    return {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "from": day, "rise": SPIKE, "p": spikes}


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [(g, (lambda g=g, c=c: build(g, c))) for g, c in GAMES.items()] + [("pokemon-zh", build_cardtrader)]
    for game, make in jobs:
        print(f"Building {game}…", flush=True)
        data = make()
        if data is None:
            continue
        n = len(data["p"])
        if n < 100:  # something went wrong upstream: keep yesterday's file rather than shipping an empty one
            print(f"  only {n} cards for {game}; keeping the existing file", file=sys.stderr)
            continue
        path = os.path.join(OUT, f"{game}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  wrote {n} {game} cards to {os.path.relpath(path)}", flush=True)
        sealed = SEALED.get(game)
        if sealed and len(sealed["p"]) >= 20:
            spath = os.path.join(OUT, f"{game}-sealed.json")
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(sealed, f, ensure_ascii=False, separators=(",", ":"))
            types = {}
            for e in sealed["p"].values():
                types[e[3]] = types.get(e[3], 0) + 1
            print(f"  wrote {len(sealed['p'])} {game} sealed products to {os.path.relpath(spath)}: {types}", flush=True)
    print("Checking 7-day price spikes…", flush=True)
    try:
        sp = build_spikes()
    except Exception as e:
        sp = None; slog(f"spike check failed: {e!r}")
    if sp:
        with open(os.path.join(OUT, "spikes.json"), "w", encoding="utf-8") as f:
            json.dump(sp, f, separators=(",", ":"))
    with open(os.path.join(OUT, "spikes-log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(SPIKE_LOG) + "\n")


if __name__ == "__main__":
    main()

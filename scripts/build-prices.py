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
    out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "groups": {}, "sets": [], "p": {}}
    for cat in cats:
        add_category(game, cat, out)
    return out


def add_category(game, cat, out):
    groups = get(f"{cat}/groups")
    for i, g in enumerate(groups, 1):
        gid = g["groupId"]
        products = get(f"{cat}/{gid}/products")
        if not products:
            continue
        prices = {}
        for r in get(f"{cat}/{gid}/prices"):
            prices.setdefault(r["productId"], []).append(r)
        kept = 0
        for p in products:
            ext = {e.get("name"): e.get("value") for e in (p.get("extendedData") or [])}
            number = (ext.get("Number") or "").strip()
            if not number:  # sealed product, not a single card
                continue
            name = p.get("name") or ""
            if name.endswith(" - " + number):
                name = name[: -len(" - " + number)]
            out["p"][str(p["productId"])] = [pick_price(prices.get(p["productId"], [])), name, number, gid, (ext.get("Rarity") or "").strip()]
            kept += 1
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


if __name__ == "__main__":
    main()

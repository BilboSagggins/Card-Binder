#!/usr/bin/env python3
"""Build compact TCGplayer price lists for the binder app from TCGCSV (https://tcgcsv.com).

TCGCSV republishes TCGplayer's catalog and market prices once a day. Browsers can't read it
directly, so this script (run daily by .github/workflows/prices.yml) copies the parts the app
needs into prices/<game>.json on the site (pokemon, pokemon-jp, onepiece):

  { "updated": "...", "groups": { "<groupId>": "<set name>" },
    "p": { "<productId>": [marketPrice, "name", "number", groupId, "rarity"] } }

Only single cards (products with a card Number) are kept.
"""
import json, os, sys, time, urllib.request

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
    out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "groups": {}, "p": {}}
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
        if i % 25 == 0:
            print(f"  {game} (category {cat}): {i}/{len(groups)} sets", flush=True)
        time.sleep(0.15)  # be gentle with a free service


def main():
    os.makedirs(OUT, exist_ok=True)
    for game, cats in GAMES.items():
        print(f"Building {game} (categories {cats})…", flush=True)
        data = build(game, cats)
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

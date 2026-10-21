#!/usr/bin/env python3
"""One-time check of CardTrader's data shapes for Chinese Pokémon. Prints to the job log; changes nothing."""
import json, os, re, sys, time, urllib.request, urllib.parse
from collections import Counter

TOKEN = os.environ.get("CARDTRADER_TOKEN", "").strip()
BASE = "https://api.cardtrader.com/api/v2"

def get(path, **params):
    url = f"{BASE}/{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "card-binder-probe"})
    for n in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and n < 2:
                time.sleep(3 + 3 * n); continue
            print(f"  ! {path}: HTTP {e.code} {e.read()[:200]!r}"); return None

if not TOKEN: sys.exit("no token")
exps = [e for e in (get("expansions") or []) if e.get("game_id") == 5]
print("ALL POKEMON EXPANSIONS (id|code|name):")
for e in sorted(exps, key=lambda e: e["id"]):
    print(f"{e['id']}|{e.get('code')}|{e.get('name')}")
print("\nEXPANSION SAMPLE:", json.dumps(exps[-1]))
cats = get("categories", game_id=5)
print("\nCATEGORIES:", json.dumps(cats)[:3000])
for eid in (4638, 3983, 3936):
    bps = get("blueprints/export", expansion_id=eid) or []
    print(f"\nBLUEPRINTS {eid}: {len(bps)}")
    for b in bps[:2] + bps[-1:]:
        print(json.dumps(b)[:2500])
    print("rarities:", Counter((b.get("fixed_properties") or {}).get("pokemon_rarity") for b in bps).most_common(30))
    print("categories:", Counter(b.get("category_id") for b in bps).most_common())
    time.sleep(1.2)
    prods = get("marketplace/products", expansion_id=eid) or {}
    for bid, lst in list(prods.items())[:1]:
        print("PRODUCT:", json.dumps(lst[0])[:2500])
    langs = Counter(); conds = Counter()
    for lst in prods.values():
        for p in lst:
            ph = p.get("properties_hash") or {}
            langs[ph.get("pokemon_language")] += 1; conds[ph.get("condition")] += 1
    print("langs:", dict(langs), "conds:", dict(conds))
    time.sleep(1.2)

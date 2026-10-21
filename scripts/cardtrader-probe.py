#!/usr/bin/env python3
"""One-time check: what Chinese Pokémon cards and prices does CardTrader have?
Reads CARDTRADER_TOKEN (a GitHub secret) and prints a report to the job log. Changes nothing."""
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
        except Exception as e:
            print(f"  ! {path}: {e}"); return None


if not TOKEN:
    sys.exit("CARDTRADER_TOKEN secret is missing")
info = get("info")
print("1) Key works:", bool(info), "| account:", (info or {}).get("name") or (info or {}).get("username") or "?")
games = get("games") or {}
games = games.get("array", games) if isinstance(games, dict) else games
poke = [g for g in games if re.search(r"pok", (g.get("name") or "") + (g.get("display_name") or ""), re.I)]
print("2) Pokémon games on CardTrader:", [(g.get("id"), g.get("display_name") or g.get("name")) for g in poke])
gids = {g["id"] for g in poke}
exps = [e for e in (get("expansions") or []) if e.get("game_id") in gids]
print(f"   Pokémon expansions: {len(exps)}")
chinese = [e for e in exps if re.search(r"chin|gem pack|\bcbb|\bcs[vmk]?\d|\bcsv|simplified|traditional|中文|简|繁", (e.get("name") or "") + " " + (e.get("code") or ""), re.I)]
print(f"3) Chinese-looking expansions: {len(chinese)}")
for e in chinese[:60]:
    print(f"   - [{e.get('code')}] {e.get('name')} (id {e.get('id')})")

# sample a few: Gem Pack first
sample = sorted(chinese, key=lambda e: (0 if re.search(r"gem", e.get("name") or "", re.I) else 1, -(e.get("id") or 0)))[:4]
for e in sample:
    print(f"\n4) Sample: {e.get('name')} [{e.get('code')}]")
    bps = get("blueprints/export", expansion_id=e["id"]) or []
    cards = [b for b in bps if (b.get("category_id") or 0) and not re.search(r"booster|box|pack|display|case|bundle", b.get("name") or "", re.I)]
    print(f"   blueprints: {len(bps)} (looks like single cards: {len(cards)})")
    time.sleep(1.2)
    prods = get("marketplace/products", expansion_id=e["id"]) or {}
    langs = Counter()
    rows = []
    for bid, lst in prods.items():
        if not lst: continue
        for p in lst:
            ph = p.get("properties_hash") or {}
            langs[ph.get("pokemon_language") or ph.get("language") or "?"] += 1
        best = min(lst, key=lambda p: (p.get("price") or {}).get("cents", 10**9))
        b = next((x for x in bps if str(x.get("id")) == str(bid)), {})
        rows.append(((best.get("price") or {}).get("cents", 0) / 100, (best.get("price") or {}).get("currency"), b.get("name") or best.get("name_en"), (b.get("fixed_properties") or {}).get("collector_number")))
    print(f"   blueprints with listings right now: {len(rows)} | listing languages: {dict(langs.most_common(6))}")
    for price, cur, name, num in sorted(rows, key=lambda r: -r[0])[:8]:
        print(f"     {name} #{num}: lowest {price:.2f} {cur}")
    time.sleep(1.2)
print("\nDone.")

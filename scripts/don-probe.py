import json, urllib.request, collections
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request("https://tcgcsv.com/tcgplayer/" + u, headers={"User-Agent": "card-binder probe"}), timeout=60).read())["results"]
F = ("Rarity", "Card Type", "CardType", "HP", "Stage", "Attack 1", "Card Text", "Weakness", "Resistance", "Retreat Cost", "Cost", "Power", "Counterplus", "Color", "Life")
for cat, groups in [(68, None), (3, 6), (85, 4)]:
    gs = get(f"{cat}/groups"); gs = gs if groups is None else gs[:groups]
    dropped = collections.Counter(); ex = []
    for g in gs:
        for p in get(f"{cat}/{g['groupId']}/products"):
            ext = {e.get("name"): e.get("value") for e in (p.get("extendedData") or [])}
            if (ext.get("Number") or "").strip(): continue
            if any((ext.get(k) or "").strip() for k in F):
                dropped[g["name"]] += 1
                if len(ex) < 25: ex.append((p["productId"], p["name"], {k: v for k, v in ext.items() if k not in ("Description",)}))
    print(f"=== category {cat}: {sum(dropped.values())} single cards without a number in {len(gs)} sets")
    print(dropped.most_common(12))
    for e in ex: print("  ", e)

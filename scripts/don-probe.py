import json, urllib.request, collections
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request("https://optcgapi.com/api/" + u, headers={"User-Agent": "Mozilla/5.0 card-binder probe"}), timeout=60).read())
    except Exception as e: return {"error": repr(e)}
don = get("allDonCards/")
print("allDonCards type:", type(don).__name__, "count:", len(don) if isinstance(don, list) else don)
if isinstance(don, list):
    print("keys:", sorted(don[0].keys()) if don else None)
    for r in don[:6]: print(json.dumps(r)[:600])
    print("set_id values:", collections.Counter(str(r.get("set_id")) for r in don).most_common(40))
    print("card_set_id values:", collections.Counter(str(r.get("card_set_id"))[:12] for r in don).most_common(15))
    print("missing image:", sum(1 for r in don if not r.get("card_image")), "missing name:", sum(1 for r in don if not r.get("card_name")))
sets = get("allSets/")
print("allSets:", [ (x.get("set_id"), x.get("set_name")) for x in sets ][:40] if isinstance(sets, list) else sets)
st = get("allSetCards/")
print("allSetCards:", len(st) if isinstance(st, list) else st, "| rarities:", collections.Counter(str(r.get("rarity")) for r in st).most_common(12) if isinstance(st, list) else "")

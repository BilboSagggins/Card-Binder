import json, urllib.request, collections, time
def get(u):
    t = time.time()
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request("https://optcgapi.com/api/" + u, headers={"User-Agent": "Mozilla/5.0 card-binder probe"}), timeout=90).read())
        return d, round(time.time() - t, 1)
    except Exception as e: return {"error": repr(e)[:200]}, round(time.time() - t, 1)
sets, t = get("allSets/"); print("allSets", t, "s")
print([(x.get("set_id"), x.get("set_name")) for x in sets] if isinstance(sets, list) else sets)
decks, t = get("allDecks/"); print("allDecks", t, "s", [(x.get("structure_deck_id"), x.get("structure_deck_name")) for x in decks][-12:] if isinstance(decks, list) else decks)
cards, t = get("allSetCards/"); print("allSetCards", t, "s")
if isinstance(cards, list):
    c = collections.Counter(str(r.get("set_id")) for r in cards); print(sorted(c.items()))
    print("newest scrape:", max(str(r.get("date_scraped")) for r in cards))
st, t = get("allSTCards/"); print("allSTCards", t, "s", sorted(collections.Counter(str(r.get("set_id")) for r in st).items())[-10:] if isinstance(st, list) else st)

"""Fix one pocket on the photo test page: pocket 11 is the Destined Rivals stamped printing (TCGplayer 663427)."""
import json, urllib.request
API = "AIzaSyDOtaK7XgGBd6Yq5nBh7Ue9yJ41DlWQRrs"; DB = "https://card-binder-9879a-default-rtdb.firebaseio.com/"; UA = {"User-Agent": "card-binder photo test"}
def req(url, data=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={**UA, "Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
tok = req(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API}", {"returnSecureToken": True})["idToken"]
EN = req("https://raw.githubusercontent.com/BilboSagggins/Card-Binder/main/prices/pokemon.json")
page = req(DB + "binders/kyle/pages/6.json?auth=" + tok)
assert page and page.get("title") == "📷 Photo test", "page 7 isn't the photo test page"
pid = "663427"; e = EN["p"][pid]
c = {"id": "tcg-" + pid, "tcgPid": int(pid), "name": e[1], "set": EN["groups"].get(str(e[3]), ""), "number": e[2], "rarity": e[4], "price": e[0],
     "url": f"https://www.tcgplayer.com/product/{pid}", "thumb": f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_200w.jpg", "image": f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg",
     "alts": [f"https://product-images.tcgplayer.com/fit-in/437x610/{pid}.jpg", f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_200w.jpg"], "game": "pokemon", "lang": "en", "source": "tcgplayer", "status": "owned"}
req(DB + "binders/kyle.json?auth=" + tok, {"pages/6/cards/10": c}, method="PATCH")
b = req(DB + "binders/kyle/pages/6/cards/10.json?auth=" + tok)
print("slot 11 now:", b["name"], "·", b["set"], "·", b["number"], "· $", b["price"])

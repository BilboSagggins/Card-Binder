"""Second step of the binder-photo test: pick the printing for the pockets whose card isn't in the collection (by name
search + picture), then append ONE new page with all the pockets to Kyle's binder. Existing pages are not touched."""
import io, json, os, re, urllib.request
API = "AIzaSyDOtaK7XgGBd6Yq5nBh7Ue9yJ41DlWQRrs"; DB = "https://card-binder-9879a-default-rtdb.firebaseio.com/"; UA = {"User-Agent": "card-binder photo test"}
RAW = "https://raw.githubusercontent.com/BilboSagggins/Card-Binder/main/prices/"
def req(url, data=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={**UA, "Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
tok = req(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API}", {"returnSecureToken": True})["idToken"]
db = lambda path: DB + path + ".json?auth=" + tok
EN = req(RAW + "pokemon.json"); ZH = req(RAW + "pokemon-zh.json")
CT = "https://cardtrader.com/uploads/blueprints/image/"
def img_url(src, pid): return f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg" if src == "en" else CT + ZH["p"][pid][5]
from PIL import Image
def load(u):
    im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read())).convert("RGB"); im.thumbnail((448, 448)); return im
import torch
from transformers import CLIPModel, CLIPProcessor
M = "openai/clip-vit-large-patch14"; model = CLIPModel.from_pretrained(M).eval(); proc = CLIPProcessor.from_pretrained(M)
def views(im):
    w, h = im.size; side = max(w, h); sq = Image.new("RGB", (side, side)); sq.paste(im, ((side - w) // 2, (side - h) // 2))
    return [sq, im.crop((int(w * .06), int(h * .08), int(w * .94), int(h * .55)))]
def emb(ims):
    with torch.no_grad():
        e = model.get_image_features(**proc(images=[v for im in ims for v in views(im)], return_tensors="pt")); e = e / e.norm(dim=-1, keepdim=True)
        e = e.view(-1, 2, e.shape[-1]).mean(1); return e / e.norm(dim=-1, keepdim=True)
# pockets whose card isn't in the collection: the printings of the name you'd type in search
fallback = {0: ("en", ["197688", "197726", "197728", "189659"]),
            4: ("zh", ["353449", "353704", "353706", "353723"]),
            10: ("en", ["630808", "633008", "633029", "663425", "663426", "663427"])}
first = json.load(open("photo-result.json"))
pick = {}
for i, row in enumerate(first):
    if row["empty"]: continue
    if i in fallback:
        src, pids = fallback[i]
        P = emb([Image.open(f"photo/p{i:02d}.jpg").convert("RGB")]); C = emb([load(img_url(src, p)) for p in pids])
        s = (P @ C.T)[0].tolist(); best = max(range(len(pids)), key=lambda j: s[j])
        print(f"pocket {i + 1}: by name + picture ->", [(pids[j], round(s[j], 3)) for j in range(len(pids))], "=> pick", pids[best])
        pick[i] = (src, pids[best], False)
    else: pick[i] = ("en", row["top"][0]["pid"], True)
coll = req(db("collections/kyle/pokemon/items")) or {}
collOf = {}
for cid, it in coll.items():
    m = re.search(r"product_(\d+)\.", str(it.get("image") or "")); 
    if m: collOf.setdefault(m.group(1), cid)
def card(src, pid):
    if src == "en":
        e = EN["p"][pid]; c = {"id": "tcg-" + pid, "tcgPid": int(pid), "name": e[1], "set": EN["groups"].get(str(e[3]), ""), "number": e[2] or "—", "rarity": e[4] or "—", "price": e[0],
             "url": f"https://www.tcgplayer.com/product/{pid}", "thumb": f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_200w.jpg", "image": f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg",
             "alts": [f"https://product-images.tcgplayer.com/fit-in/437x610/{pid}.jpg", f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_200w.jpg"], "game": "pokemon", "lang": "en", "source": "tcgplayer", "status": "owned"}
        if pid in collOf: c["collId"] = collOf[pid]
        return {k: v for k, v in c.items() if v is not None}
    e = ZH["p"][pid]; img = CT + e[5]; show = CT + re.sub(r"([^/]+)$", r"show_\1", e[5])
    c = {"id": "ct-" + pid, "ctId": int(pid), "name": e[1], "set": (ZH.get("groups") or {}).get(str(e[3]), ""), "number": e[2] or "—", "rarity": e[4] or "—", "price": e[0],
         "url": f"https://www.cardtrader.com/cards/{pid}", "thumb": show, "image": img, "alts": [show, img], "game": "pokemon", "lang": "zh", "source": "cardtrader", "status": "owned"}
    return {k: v for k, v in c.items() if v is not None}
cards = [None] * 12
for i, (src, pid, auto) in pick.items(): cards[i] = card(src, pid)
for i, c in enumerate(cards): print(f"slot {i + 1:2d}:", (c["name"] + " · " + c["set"] + " · " + c["number"] + f" · ${c.get('price')}" + (" · in collection" if c.get("collId") else "")) if c else "(empty)")
# append ONE page after the existing ones
keys = req(DB + "binders/kyle/pages.json?shallow=true&auth=" + tok) or {}
keys = list(range(len(keys))) if isinstance(keys, list) else [int(k) for k in keys]
n = max(keys) + 1 if keys else 0
assert req(db(f"binders/kyle/pages/{n}")) is None, "that page number is taken"
page = {"title": "📷 Photo test", "cards": cards}
req(db("binders/kyle"), {f"pages/{n}": page}, method="PATCH")
back = req(db(f"binders/kyle/pages/{n}")); after = req(DB + "binders/kyle/pages.json?shallow=true&auth=" + tok)
print(f"wrote page {n + 1} ('{back['title']}'), pages before {len(keys)}, after {len(after)}; cards saved: {sum(1 for c in (back.get('cards') or []) if c)}")

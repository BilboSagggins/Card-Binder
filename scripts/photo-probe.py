"""Identify the cards in a photographed binder page by comparing each pocket with the pictures of the cards in the
owner's collection (CLIP image matching). Read-only: nothing is written to the binder."""
import io, json, os, re, sys, glob, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
API = "AIzaSyDOtaK7XgGBd6Yq5nBh7Ue9yJ41DlWQRrs"; DB = "https://card-binder-9879a-default-rtdb.firebaseio.com/"
UA = {"User-Agent": "card-binder photo test"}
def req(url, data=None):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={**UA, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
tok = req(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API}", {"returnSecureToken": True})["idToken"]
get = lambda path: req(DB + path + ".json?auth=" + tok)
info = get("binderInfo") or {}; users = get("users") or {}
owner = "kyle"
mine = [owner] + [b for b, v in info.items() if v and v.get("owner") == owner]
print("binders:", [(b, (info.get(b) or {}).get("title"), (info.get(b) or {}).get("game", "pokemon")) for b in mine])
for b in mine:
    lay = get(f"binders/{b}/layout"); pages = req(DB + f"binders/{b}/pages.json?shallow=true&auth=" + tok) or {}
    print("  ", b, "layout", lay, "pages", len(pages) if isinstance(pages, (dict, list)) else pages)
coll = (get(f"collections/{owner}/pokemon") or {}).get("items") or {}
cands = {}
for cid, it in coll.items():
    m = re.search(r"product_(\d+)\.", str(it.get("image") or ""))
    if m: cands.setdefault(m.group(1), it)
print("collection:", len(coll), "entries,", len(cands), "with a picture to compare")
from PIL import Image
def load(pid):
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg", headers=UA), timeout=40).read())).convert("RGB")
        im.thumbnail((448, 448)); return pid, im
    except Exception: return pid, None
with ThreadPoolExecutor(16) as p: imgs = {pid: im for pid, im in p.map(load, list(cands)) if im is not None}
print("downloaded", len(imgs))
import torch
from transformers import CLIPModel, CLIPProcessor
torch.set_num_threads(os.cpu_count() or 2)
M = "openai/clip-vit-large-patch14"; model = CLIPModel.from_pretrained(M).eval(); proc = CLIPProcessor.from_pretrained(M)
def card_box(im):
    """trim to the card itself: TCGplayer pictures have white margins"""
    return im
def views(im):
    w, h = im.size; side = max(w, h); sq = Image.new("RGB", (side, side)); sq.paste(im, ((side - w) // 2, (side - h) // 2))
    return [sq, im.crop((int(w * .06), int(h * .08), int(w * .94), int(h * .55)))]
def embed(ims):
    out = []
    with torch.no_grad():
        for i in range(0, len(ims), 16):
            vs = [v for im in ims[i:i + 16] for v in views(im)]
            e = model.get_image_features(**proc(images=vs, return_tensors="pt")); e = e / e.norm(dim=-1, keepdim=True)
            e = e.view(-1, 2, e.shape[-1]).mean(1); out.append(e / e.norm(dim=-1, keepdim=True))
    return torch.cat(out)
pids = list(imgs); C = embed([imgs[p] for p in pids])
crops = sorted(glob.glob("photo/p*.jpg")); P = embed([Image.open(f).convert("RGB") for f in crops])
with torch.no_grad():
    t = model.get_text_features(**proc(text=["an empty clear plastic binder pocket", "a pokemon trading card"], return_tensors="pt", padding=True)); t = t / t.norm(dim=-1, keepdim=True)
S = P @ C.T; E = (P @ t.T)
res = []
for i, f in enumerate(crops):
    top = torch.topk(S[i], min(5, len(pids)))
    empty = bool(E[i][0] > E[i][1])
    row = {"pocket": i, "empty": empty, "top": [{"pid": pids[j], "score": round(float(s), 3), "name": cands[pids[j]].get("name"), "set": cands[pids[j]].get("set"), "number": cands[pids[j]].get("number")} for s, j in zip(top.values.tolist(), top.indices.tolist())]}
    res.append(row)
    print(f"pocket {i + 1:2d} {'EMPTY ' if empty else ''}->", " | ".join(f"{x['name']} {x['number']} ({x['score']})" for x in row["top"][:3]))
json.dump(res, open("photo-result.json", "w"), indent=1)
from PIL import ImageDraw
sheet = Image.new("RGB", (4 * 150, 12 * 210), (20, 20, 24)); d = ImageDraw.Draw(sheet)
for i, f in enumerate(crops):
    a = Image.open(f).convert("RGB"); a.thumbnail((146, 204)); sheet.paste(a, (2, i * 210 + 2))
    for k, x in enumerate(res[i]["top"][:3]):
        b = imgs[x["pid"]].copy(); b.thumbnail((146, 190)); sheet.paste(b, (152 + k * 150, i * 210 + 2)); d.text((152 + k * 150, i * 210 + 192), f"{x['score']}", fill=(255, 255, 0))
sheet.save("photo-sheet.jpg", quality=80)

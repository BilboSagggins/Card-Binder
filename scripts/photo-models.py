"""Same binder photo, smaller CLIP models (the sizes a phone browser can run). Read-only."""
import io, json, os, re, glob, urllib.request
from concurrent.futures import ThreadPoolExecutor
API = "AIzaSyDOtaK7XgGBd6Yq5nBh7Ue9yJ41DlWQRrs"; DB = "https://card-binder-9879a-default-rtdb.firebaseio.com/"; UA = {"User-Agent": "card-binder photo test"}
def req(url, data=None):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={**UA, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
tok = req(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API}", {"returnSecureToken": True})["idToken"]
coll = req(DB + "collections/kyle/pokemon/items.json?auth=" + tok) or {}
cands = {}
for cid, it in coll.items():
    m = re.search(r"product_(\d+)\.", str(it.get("image") or "")); 
    if m: cands.setdefault(m.group(1), it.get("name"))
from PIL import Image
def load(pid):
    try:
        im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg", headers=UA), timeout=40).read())).convert("RGB"); im.thumbnail((448, 448)); return pid, im
    except Exception: return pid, None
with ThreadPoolExecutor(16) as p: imgs = {pid: im for pid, im in p.map(load, list(cands)) if im is not None}
truth = {1: "197726", 2: "197728", 3: "189659", 8: "623588", 9: "517048", 11: "111643"}     # pockets (0-based) whose card is in the collection
empty = {5, 6, 7}
import torch
from transformers import CLIPModel, CLIPProcessor
torch.set_num_threads(os.cpu_count() or 2)
crops = sorted(glob.glob("photo/p*.jpg")); pims = [Image.open(f).convert("RGB") for f in crops]
def views(im, mode):
    w, h = im.size
    if mode == "full": return [im]
    side = max(w, h); sq = Image.new("RGB", (side, side)); sq.paste(im, ((side - w) // 2, (side - h) // 2))
    return [sq, im.crop((int(w * .06), int(h * .08), int(w * .94), int(h * .55)))]
out = {}
for M in ["openai/clip-vit-base-patch16", "openai/clip-vit-base-patch32", "openai/clip-vit-large-patch14"]:
    model = CLIPModel.from_pretrained(M).eval(); proc = CLIPProcessor.from_pretrained(M)
    def emb(ims, mode):
        res = []
        with torch.no_grad():
            for i in range(0, len(ims), 16):
                vs = [v for im in ims[i:i + 16] for v in views(im, mode)]; n = len(vs) // len(ims[i:i + 16])
                e = model.get_image_features(**proc(images=vs, return_tensors="pt")); e = e / e.norm(dim=-1, keepdim=True)
                e = e.view(-1, n, e.shape[-1]).mean(1); res.append(e / e.norm(dim=-1, keepdim=True))
        return torch.cat(res)
    with torch.no_grad():
        t = model.get_text_features(**proc(text=["an empty clear plastic binder pocket", "a pokemon trading card"], return_tensors="pt", padding=True)); t = t / t.norm(dim=-1, keepdim=True)
    pids = list(imgs)
    for mode in ["full", "two"]:
        C = emb([imgs[p] for p in pids], mode); P = emb(pims, mode); S = P @ C.T; E = P @ t.T
        ok = sum(1 for i, pid in truth.items() if pids[int(S[i].argmax())] == pid)
        emp = sum(1 for i in range(len(crops)) if (bool(E[i][0] > E[i][1])) == (i in empty))
        gaps = [round(float(torch.topk(S[i], 2).values[0] - torch.topk(S[i], 2).values[1]), 3) for i in truth]
        tops = [round(float(S[i].max()), 3) for i in range(len(crops))]
        print(f"{M.split('/')[-1]:24s} {mode:4s}: in-collection right {ok}/{len(truth)} | empty right {emp}/12 | gap to 2nd {gaps} | best scores {tops}", flush=True)
    if M.endswith("patch16"): out = {"model": M, "empty": t[0].tolist(), "card": t[1].tolist()}
json.dump(out, open("photo-text-b16.json", "w"))

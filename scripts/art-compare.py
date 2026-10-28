"""Compare ways of tagging card art on the same 580-card sample: which model, and whether the card's printed text is hidden."""
import io, json, os, sys, time, urllib.request, importlib.util
from concurrent.futures import ThreadPoolExecutor
spec = importlib.util.spec_from_file_location("bat", "scripts/build-art-tags.py"); bat = importlib.util.module_from_spec(spec); spec.loader.exec_module(bat)
import torch
from PIL import Image, ImageFilter, ImageDraw
torch.set_num_threads(os.cpu_count() or 2)
VOCAB, PROMPTS = bat.VOCAB, bat.PROMPTS
pids = list(json.load(open("trial-cards.json"))["cards"])
def load(pid):
    try:
        im = Image.open(io.BytesIO(bat.fetch(bat.IMG.format(pid=pid)))).convert("RGB"); im.thumbnail((448, 448)); return pid, im
    except Exception: return pid, None
with ThreadPoolExecutor(16) as p: ims = {pid: im for pid, im in p.map(load, pids) if im is not None}
pids = [p for p in pids if p in ims]; print(len(pids), "pictures", flush=True)

def masked(im):
    """the card with its name bar and text box blurred so the model can't read words"""
    w, h = im.size; out = im.copy()
    for box in [(0, 0, w, int(h * .11)), (0, int(h * .55), w, h)]:
        out.paste(im.crop(box).filter(ImageFilter.GaussianBlur(10)), box[:2])
    return out
def views(im, mask):
    full = masked(im) if mask else im
    w, h = im.size; side = max(w, h); sq = Image.new("RGB", (side, side)); sq.paste(full, ((side - w) // 2, (side - h) // 2))
    art = im.crop((int(w * .07), int(h * .10), int(w * .93), int(h * .53)))
    return [sq, art]

def run(name, model_id, kind, mask):
    t0 = time.time()
    if kind == "clip":
        from transformers import CLIPModel, CLIPProcessor
        m = CLIPModel.from_pretrained(model_id).eval(); pr = CLIPProcessor.from_pretrained(model_id); tk = dict(padding=True)
    else:
        from transformers import AutoModel, AutoProcessor
        m = AutoModel.from_pretrained(model_id).eval(); pr = AutoProcessor.from_pretrained(model_id); tk = dict(padding="max_length")
    with torch.no_grad():
        texts = [p.format(v) for v in VOCAB for p in PROMPTS]; T = []
        for i in range(0, len(texts), 128):
            t = m.get_text_features(**pr(text=texts[i:i + 128], return_tensors="pt", **tk)); T.append(t / t.norm(dim=-1, keepdim=True))
        T = torch.cat(T).view(len(VOCAB), len(PROMPTS), -1).mean(1); T = T / T.norm(dim=-1, keepdim=True)
        E = []
        for i in range(0, len(pids), 16):
            vs = [v for p in pids[i:i + 16] for v in views(ims[p], mask)]
            e = m.get_image_features(**pr(images=vs, return_tensors="pt")); e = e / e.norm(dim=-1, keepdim=True)
            e = e.view(-1, 2, e.shape[-1]).mean(1); E.append(e / e.norm(dim=-1, keepdim=True))
        E = torch.cat(E)
    S = E @ T.T; Z = (S - S.mean(0)) / S.std(0).clamp(min=1e-6)
    tags = {}
    for i, p in enumerate(pids):
        rank = torch.argsort(S[i], descending=True)[:20].tolist()
        tags[p] = [[j, round(float(Z[i][j]), 2)] for j in rank if Z[i][j] > 1.8]
    print(f"{name}: {time.time() - t0:.0f}s", flush=True)
    return tags

V = [("A_now", "openai/clip-vit-base-patch16", "clip", False),
     ("B_hide_text", "openai/clip-vit-base-patch16", "clip", True),
     ("C_siglip", "google/siglip-base-patch16-224", "siglip", True),
     ("D_clip_large", "openai/clip-vit-large-patch14", "clip", True)]
out = {"vocab": VOCAB, "pids": pids, "variants": {}}
for v in V:
    try: out["variants"][v[0]] = run(*v)
    except Exception as e: print(v[0], "failed:", repr(e)[:300], flush=True)
json.dump(out, open("art-compare.json", "w"), separators=(",", ":"))

# picture grids: one per word, a row per variant (best 8 at the strict level)
os.makedirs("cmp", exist_ok=True)
WORDS = ["moon", "beach", "snow", "night sky", "flowers", "city", "food", "cake", "rain", "underwater", "sleeping", "christmas tree", "halloween", "surfboard", "eclipse", "rainbow", "forest", "lightning"]
for w in WORDS:
    j = VOCAB.index(w); names = list(out["variants"])
    sheet = Image.new("RGB", (8 * 110 + 120, len(names) * 160 + 10), (20, 20, 24)); d = ImageDraw.Draw(sheet)
    for r, n in enumerate(names):
        hits = sorted(((z, p) for p, ts in out["variants"][n].items() for jj, z in ts if jj == j and z > 2.3), reverse=True)
        d.text((4, r * 160 + 60), f"{n}\n{len(hits)} cards", fill=(255, 255, 255))
        for k, (z, p) in enumerate(hits[:8]):
            t = ims[p].copy(); t.thumbnail((106, 150)); sheet.paste(t, (120 + k * 110, r * 160 + 5))
    sheet.save(f"cmp/{w.replace(' ', '_')}.jpg", quality=78)
for n, tags in out["variants"].items():
    strict = sum(1 for ts in tags.values() if any(z > 2.3 for _, z in ts)); loose = sum(1 for ts in tags.values() if ts)
    print(f"{n}: cards with a tag strict {strict}/{len(pids)}, loose {loose}/{len(pids)}")

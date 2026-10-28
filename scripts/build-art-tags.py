"""Tag what's in each card's artwork (moon, beach, snow, night sky, food...) so the app can search by art.

Uses CLIP, a free open-source model that matches pictures with words (openai/clip-vit-large-patch14), on the GitHub
runner's CPU. No paid AI service and no key. Each card picture is looked at once; results are kept in
prices/art-tags.json, so every run only does cards it hasn't seen (new sets, or the rest of a long first scan).

  python3 scripts/build-art-tags.py --limit 4000          # tag up to 4000 new cards this run
  python3 scripts/build-art-tags.py --trial 300 --sheets  # a random sample, plus picture grids per tag for checking

Output (compact): { model, updated, vocab: [concept...], done: n, t: { tcgplayerId: [[conceptIndex, score], ...] },
                   stats: { mean: [...], std: [...] } }   (stats: per-concept similarity, so new cards are scored the same way)
"""
import argparse, io, json, os, random, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "prices", "art-tags.json")
LIST_URL = "https://raw.githubusercontent.com/BilboSagggins/Card-Binder/main/prices/pokemon.json"
IMG = "https://tcgplayer-cdn.tcgplayer.com/product/{pid}_in_1000x1000.jpg"
MODEL = "openai/clip-vit-large-patch14"
# Oct 2026 comparison on 580 cards (base CLIP, base CLIP with text hidden, SigLIP, large CLIP with text hidden): the large
# model with the card's words blurred was clearly best. Without blurring, CLIP reads the card: "Food Prep" -> food,
# the Cosmic Eclipse stamp -> eclipse.
UA = "card-binder-art-tags (github.com/BilboSagggins/Card-Binder)"

# Everyday things people remember about a card's art. One word or short phrase each; the app searches these.
VOCAB = """moon|full moon|crescent moon|sun|sunset|sunrise|night sky|starry sky|stars|galaxy|outer space|planet|comet|rainbow|clouds|storm clouds|lightning|rain|snow|snowflakes|ice|icicles|blizzard|fog|wind|tornado|
fire|flames|lava|volcano|smoke|explosion|sparkles|light beams|aurora|eclipse|
ocean|sea waves|underwater|beach|sand|island|lake|river|waterfall|pond|swamp|bubbles|coral reef|seaweed|shipwreck|boat|ship|surfboard|
mountain|cliff|cave|canyon|desert|forest|jungle|trees|autumn leaves|cherry blossoms|flowers|flower field|roses|sunflowers|tulips|grass|meadow|garden|mushrooms|vines|bamboo|cactus|palm trees|rocks|crystals|gems|gold coins|treasure chest|
city|city skyline|buildings|skyscrapers|street|road|bridge|train|train tracks|car|bicycle|airplane|hot air balloon|tower|castle|ruins|temple|shrine|torii gate|pagoda|lighthouse|windmill|house|cabin|tent|campfire|fence|stairs|
kitchen|restaurant|cafe|bakery|food|fruit|apples|berries|cake|cupcake|candy|ice cream|donut|cookies|bread|pizza|noodles|sushi|rice ball|tea|coffee|bowl|picnic|
toys|ball|balloons|kite|umbrella|hat|scarf|crown|glasses|backpack|book|books|library|school|classroom|desk|computer|television|phone|camera|clock|lamp|lantern|candles|mirror|window|bed|pillow|blanket|bath|bathtub|
music|guitar|piano|drum|microphone|stage|concert|dance|party|festival|fireworks|confetti|gift box|christmas tree|pumpkin|halloween|ghost|spooky|graveyard|haunted house|cobwebs|skull|
sports|soccer ball|baseball|basketball|tennis|swimming|running|race|trophy|medal|
museum|art gallery|painting|sculpture|statue|playground|park|zoo|farm|barn|field|hay|
sleeping|eating|swimming pokemon|flying|jumping|running pokemon|fighting|battle|hugging|friends|family|baby|egg|nest|
trainer|person|child|girl|boy|old man|crowd|chef|doctor|nurse|police|scientist|
laboratory|machine|robot|gears|factory|power lines|electricity|neon lights|
pink|purple|blue|green|red|orange|yellow|black and white|dark|bright colors|pastel colors|watercolor|pixel art|cartoon|realistic|3d render|
reflection|shadow|silhouette|close-up|landscape|night|daytime|winter|spring|summer|autumn|heart|hearts|star shape|circle|stripes|polka dots|patterns|map|flag|sign|letters|numbers""".replace("\n", "")
VOCAB = [v.strip() for v in VOCAB.split("|") if v.strip()]
# words that matched almost anything in the trial (people's jobs, colours, drawing styles): left out
DROP = set("""3d render|baby|backpack|ball|baseball|basketball|black and white|blue|bowl|boy|bright colors|cartoon|chef|child|circle|close-up|crowd|crown|dark|daytime|desk|doctor|family|flag|friends|girl|glasses|green|hat|heart|hearts|landscape|letters|light beams|map|medal|numbers|nurse|old man|orange|pastel colors|patterns|pink|pixel art|police|polka dots|purple|race|realistic|red|reflection|running|scarf|scientist|shadow|sign|soccer ball|sparkles|sports|star shape|stripes|swimming|tennis|trainer|watercolor|yellow""".split("|"))
VOCAB = [v for v in VOCAB if v not in DROP]
PROMPTS = ["a trading card illustration with {}", "artwork showing {}", "a picture of {}"]


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_image(pid):
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(fetch(IMG.format(pid=pid)))).convert("RGB")
        im.thumbnail((448, 448))
        return pid, im
    except Exception:
        return pid, None


def hide_text(im):
    """The card with its name bar and text box blurred, so the model looks at the picture instead of reading words."""
    from PIL import ImageFilter
    w, h = im.size; out = im.copy()
    for box in [(0, 0, w, int(h * .11)), (0, int(h * .55), w, h)]:
        out.paste(im.crop(box).filter(ImageFilter.GaussianBlur(10)), box[:2])
    return out


def views(im):
    """Two looks at a card: the whole card with its words blurred (letterboxed), and the artwork window near the top."""
    from PIL import Image
    w, h = im.size
    side = max(w, h); full = Image.new("RGB", (side, side), (0, 0, 0)); full.paste(hide_text(im), ((side - w) // 2, (side - h) // 2))
    art = im.crop((int(w * .07), int(h * .10), int(w * .93), int(h * .53)))
    return full, art


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4000)
    ap.add_argument("--trial", type=int, default=0)
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    import torch
    from transformers import CLIPModel, CLIPProcessor
    torch.set_num_threads(os.cpu_count() or 2)

    lst = json.loads(fetch(LIST_URL, 60))["p"]
    prev = {}
    if os.path.exists(a.out) and not a.trial:
        with open(a.out, encoding="utf-8") as f:
            prev = json.load(f)
    if prev.get("vocab") and prev["vocab"] != VOCAB:
        print("vocabulary changed: re-tagging everything"); prev = {}
    # a new model: start over, but keep the earlier tags for cards not redone yet, so search keeps working.
    # "t" always holds every card's current tags; "old_ids" lists the cards still on the earlier model's tags.
    old_ids = set(prev.get("old_ids", []))
    old = {p: v for p, v in prev.get("t", {}).items() if p in old_ids}
    if prev.get("model") and prev["model"] != MODEL:
        print(f"model changed ({prev['model']} -> {MODEL}): re-tagging everything, earlier tags kept meanwhile")
        old = {**prev.get("t", {})}; prev = {"miss": prev.get("miss", {})}
    done = {p: v for p, v in prev.get("t", {}).items() if p not in old}
    # cards with no picture on TCGplayer yet: skipped, and tried again after two weeks
    miss = {p: d for p, d in prev.get("miss", {}).items() if p in lst and p not in done}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    retry_before = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 14 * 86400))
    todo = [pid for pid in lst if pid not in done and not (pid in miss and miss[pid] > retry_before)]
    if a.trial:
        random.seed(7); todo = random.sample(list(lst), min(a.trial, len(lst)))
    else:
        todo.sort(key=lambda pid: -int(pid))        # newest cards first
        if not prev.get("stats"):                   # the first run sets each word's typical score: use cards from every era
            random.seed(11); random.shuffle(todo)
        todo = todo[:a.limit]
    print(f"{len(lst)} cards in the list, {len(done)} already tagged, doing {len(todo)}")
    if not todo:
        return

    model = CLIPModel.from_pretrained(MODEL).eval(); proc = CLIPProcessor.from_pretrained(MODEL)
    with torch.no_grad():
        texts = [p.format(v) for v in VOCAB for p in PROMPTS]
        T = []
        for i in range(0, len(texts), 256):
            t = model.get_text_features(**proc(text=texts[i:i + 256], return_tensors="pt", padding=True))
            T.append(t / t.norm(dim=-1, keepdim=True))
        T = torch.cat(T).view(len(VOCAB), len(PROMPTS), -1).mean(1)
        T = T / T.norm(dim=-1, keepdim=True)

    t0 = time.time(); embs = {}
    with ThreadPoolExecutor(16) as pool:
        batch = []
        def run(batch):
            ims = [v for _, im in batch for v in views(im)]
            with torch.no_grad():
                e = model.get_image_features(**proc(images=ims, return_tensors="pt"))
                e = e / e.norm(dim=-1, keepdim=True)
                e = e.view(len(batch), 2, -1).mean(1); e = e / e.norm(dim=-1, keepdim=True)
            for (pid, _), row in zip(batch, e): embs[pid] = row
        for pid, im in pool.map(load_image, todo):
            if im is None: continue
            batch.append((pid, im))
            if len(batch) == 32: run(batch); batch = []
            if len(embs) and len(embs) % 512 == 0: print(f"  {len(embs)} cards, {time.time() - t0:.0f}s", flush=True)
        if batch: run(batch)
    print(f"looked at {len(embs)} cards in {time.time() - t0:.0f}s")
    lost = [p for p in todo if p not in embs]
    fresh = [p for p in todo if p not in miss]; fresh_lost = [p for p in fresh if p not in embs]
    outage = len(fresh_lost) > max(50, len(fresh) // 2)     # most new pictures failing = a network problem, not missing pictures
    for pid in lost:
        if pid in miss or not outage: miss[pid] = today
    print(f"{len(lost)} cards had no picture" + (" (looks like a network problem: new ones tried again next run)" if outage else " (tried again in two weeks)"))

    def save(mean, std):
        out = {"model": MODEL, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "vocab": VOCAB,
               "done": len(done) + len(miss), "tagged": len(done), "total": len(lst),
               "stats": {"mean": [round(float(x), 5) for x in mean], "std": [round(float(x), 5) for x in std]}, "miss": miss,
               "old_ids": sorted(old, key=int), "t": {**old, **done}}
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f, separators=(",", ":"))
        print(f"saved {len(done)} tagged cards ({len(miss)} without a picture) to {a.out}")

    if not embs:                      # nothing new could be looked at: just remember the cards without pictures
        if prev.get("stats"): save(prev["stats"]["mean"], prev["stats"]["std"])
        return
    pids = list(embs)
    S = torch.stack([embs[p] for p in pids]) @ T.T          # card x concept similarity
    # each concept's typical similarity (kept from the first big run so later cards are scored the same way)
    if prev.get("stats") and not a.trial:
        mean = torch.tensor(prev["stats"]["mean"]); std = torch.tensor(prev["stats"]["std"])
    else:
        mean, std = S.mean(0), S.std(0).clamp(min=1e-4)
    Z = (S - mean) / std
    tags = {}
    for i, pid in enumerate(pids):
        z = Z[i]; s = S[i]
        rank = torch.argsort(s, descending=True)[:25].tolist()     # what this card is most like overall
        keep = [(j, float(z[j])) for j in rank[:20] if z[j] > 1.8]     # 2.3+ = clear match; 1.8-2.3 = likely (listed after)
        keep.sort(key=lambda x: -x[1])
        tags[pid] = [[j, round(v, 1)] for j, v in keep[:10]]
    done.update(tags)
    for pid in tags: miss.pop(pid, None); old.pop(pid, None)
    save(mean, std)

    if a.sheets:          # picture grids of the best matches for some tags, for checking by eye
        from PIL import Image, ImageDraw
        os.makedirs("sheets", exist_ok=True)
        thumbs = {}
        for name in ["moon", "night", "beach", "snow", "food", "rain", "city", "flowers", "fire", "ocean", "sun", "cake", "forest", "underwater", "sleeping", "christmas tree", "halloween", "music", "person", "stars"]:
            j = VOCAB.index(name)
            best = sorted(((float(Z[i][j]), pids[i]) for i in range(len(pids)) if any(t[0] == j for t in tags[pids[i]])), reverse=True)[:12]
            sheet = Image.new("RGB", (6 * 150, 2 * 210 + 30), (20, 20, 24)); d = ImageDraw.Draw(sheet)
            d.text((6, 6), f"{name}: {len([1 for p in pids if any(t[0] == j for t in tags[p])])} cards tagged (best 12 shown)", fill=(255, 255, 255))
            for k, (zz, pid) in enumerate(best):
                if pid not in thumbs:
                    _, im = load_image(pid); thumbs[pid] = im
                im = thumbs[pid]
                if im is None: continue
                t = im.copy(); t.thumbnail((146, 204)); sheet.paste(t, (2 + (k % 6) * 150, 30 + (k // 6) * 210))
            sheet.save(f"sheets/{name.replace(' ', '_')}.jpg", quality=80)
        with open("sheets/summary.txt", "w") as f:
            for j, v in enumerate(VOCAB):
                n = sum(1 for p in pids if any(t[0] == j for t in tags[p]))
                f.write(f"{n:4d}  {v}\n")
            f.write("\nsample cards:\n")
            for pid in pids[:40]:
                f.write(f"{pid} {lst[pid][1]} | " + ", ".join(f"{VOCAB[j]}({z})" for j, z in tags[pid]) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""emb/all.bin + emb/pca.bin: a compact index of every card's picture fingerprint, so the 📷 Photo page can find cards that
aren't in your collection. Each 512-number fingerprint is boiled down to 64 numbers (the directions that matter most across all
cards, PCA), about 5 MB for all of them. The phone scans that in a few milliseconds per pocket, then checks the 40 closest
cards exactly with their full fingerprints (emb/<list>/<set>.bin). Tested: the right card is in those 40 about 99.5% of the time.

  emb/pca.bin: float32 little-endian, 64 scales, then 64 x 512 directions (kept once made, so the index only grows)
  emb/all.bin: one record per card, [list: uint8][card id: uint32][set id: uint32][64 x int8]
Lists are numbered as in LISTS below (also written to emb/index.json under "all")."""
import glob, json, os
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EMB = os.path.join(ROOT, 'emb')
LISTS = ['onepiece', 'pokemon', 'pokemon-zh', 'pokemon-jp']
K = 64

recs, vecs = [], []
for li, lst in enumerate(LISTS):
    for f in sorted(glob.glob(os.path.join(EMB, lst, '*.bin'))):
        gid = int(os.path.basename(f)[:-4])
        b = np.fromfile(f, dtype=np.uint8); n = len(b) // 520
        if not n:
            continue
        r = b[:n * 520].reshape(n, 520)
        ids = r[:, :4].copy().view('<u4')[:, 0]
        sc = r[:, 4:8].copy().view('<f4')[:, 0]
        v = r[:, 8:].view(np.int8).astype(np.float32) * sc[:, None]
        keep = sc > 0
        for i in np.nonzero(keep)[0]:
            recs.append((li, int(ids[i]), gid))
        vecs.append(v[keep])
X = np.concatenate(vecs); X /= np.linalg.norm(X, axis=1, keepdims=True)
print('cards', X.shape[0])

pca_path = os.path.join(EMB, 'pca.bin')
if os.path.exists(pca_path):            # keep the directions, so old cards' codes don't change
    raw = np.fromfile(pca_path, dtype='<f4'); scale, P = raw[:K], raw[K:].reshape(K, 512)
    mean = None
else:
    rng = np.random.default_rng(0)
    S = X[rng.choice(len(X), min(20000, len(X)), replace=False)]
    mean = S.mean(0)
    _, _, Vt = np.linalg.svd(S - mean, full_matrices=False)
    P = Vt[:K].astype(np.float32)
    C = X @ P.T
    scale = (np.abs(C).max(0) / 127).astype(np.float32)
    np.concatenate([scale, P.ravel()]).astype('<f4').tofile(pca_path)
# codes: the projection of each fingerprint (no centering needed for ranking: the query's dot with the mean is the same for every card)
C = np.clip(np.round((X @ P.T) / scale), -127, 127).astype(np.int8)
out = np.zeros(len(recs), dtype=[('l', 'u1'), ('id', '<u4'), ('g', '<u4'), ('c', 'i1', (K,))])
out['l'] = [r[0] for r in recs]; out['id'] = [r[1] for r in recs]; out['g'] = [r[2] for r in recs]; out['c'] = C
out.tofile(os.path.join(EMB, 'all.bin'))
idx_path = os.path.join(EMB, 'index.json')
idx = json.load(open(idx_path))
# Each list's pictures have their own look (CardTrader's Chinese pictures are photos, TCGplayer's are scans), which makes a
# whole list seem close to any photo. The phone takes that out: score - query . (list average - Pokemon average). On the Sky
# Legends test page this took the right Pokemon from first in 4 of 9 pockets to 5 of 9, and among the 8 closest from 7 to 8.
lst_of = np.array([r[0] for r in recs])
pk = np.isin(lst_of, [LISTS.index(l) for l in ('pokemon', 'pokemon-zh', 'pokemon-jp')])
gmean = X[pk].mean(0)
style = {l: [round(float(x), 5) for x in (X[lst_of == i].mean(0) - (gmean if l != 'onepiece' else X[lst_of == i].mean(0)))] for i, l in enumerate(LISTS) if (lst_of == i).any()}
idx['all'] = {'dims': K, 'cards': len(recs), 'lists': LISTS, 'record': 1 + 4 + 4 + K, 'style': style}
json.dump(idx, open(idx_path, 'w'))
print('wrote emb/all.bin', os.path.getsize(os.path.join(EMB, 'all.bin')) // 1024, 'KB')

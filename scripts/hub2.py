import json, numpy as np, os, glob, sys
# pocket vectors from hub.mjs (saved), all fingerprints
X, meta = [], []
for lst in ['pokemon', 'pokemon-zh', 'pokemon-jp']:
    L = json.load(open(f'prices/{lst}.json'))
    for f in sorted(glob.glob(f'emb/{lst}/*.bin')):
        b = np.fromfile(f, dtype=np.uint8); n = len(b) // 520; r = b[:n * 520].reshape(n, 520)
        ids = r[:, :4].copy().view('<u4')[:, 0]; sc = r[:, 4:8].copy().view('<f4')[:, 0]
        v = r[:, 8:].view(np.int8).astype(np.float32) * sc[:, None]
        for i in range(n):
            if sc[i] > 0: X.append(v[i]); e = L['p'][str(ids[i])]; meta.append((e[1], L['groups'].get(str(e[3]), ''), lst))
X = np.array(X); X /= np.linalg.norm(X, axis=1, keepdims=True)
Q = json.load(open('pockets.json'))
want = {'1': 'moltres & zapdos', '2': 'moltres & zapdos', '3': 'moltres & zapdos', '4': 'moltres & zapdos', '5': 'moltres & zapdos', '9': 'articuno', '10': 'zapdos', '11': 'moltres', '12': 'ho-oh'}
# how crowded each card's neighbourhood is: mean similarity to its 10 nearest other cards
r = np.zeros(len(X), np.float32)
for s in range(0, len(X), 4000):
    S = X[s:s + 4000] @ X.T
    S[np.arange(S.shape[0]), np.arange(s, s + S.shape[0])] = -1
    r[s:s + 4000] = np.sort(S, axis=1)[:, -10:].mean(1)
print('crowding: mean %.3f, max %.3f; zh %.3f jp %.3f en %.3f' % (r.mean(), r.max(), *[r[[m[2] == l for m in meta]].mean() for l in ('pokemon-zh', 'pokemon-jp', 'pokemon')]))
gm = X.mean(0)
for name, base in [('raw', lambda q: X @ q), ('centered', lambda q: ((X - gm) / np.linalg.norm(X - gm, axis=1, keepdims=True)) @ ((q - gm) / np.linalg.norm(q - gm)))]:
    for a in (0, 0.5, 0.75, 1.0):
        ok = 0; lines = []
        for k, q in Q.items():
            q = np.array(q, np.float32); s = base(q) - a * r
            top = np.argsort(-s)[:3]; good = want[k] in meta[top[0]][0].lower(); ok += good
            lines.append(f'   {k}: {"OK " if good else "no "}' + ' | '.join(f'{meta[i][0]} [{meta[i][1]}] {s[i]:.3f}' for i in top))
        print(f'== {name}, discount {a}: {ok} of {len(Q)}'); 
        if a in (0.75, 1.0): print('\n'.join(lines))

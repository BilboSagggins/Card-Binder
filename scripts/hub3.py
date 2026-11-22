import json, numpy as np, glob
X, meta, lists = [], [], []
for lst in ['pokemon', 'pokemon-zh', 'pokemon-jp']:
    L = json.load(open(f'prices/{lst}.json'))
    for f in sorted(glob.glob(f'emb/{lst}/*.bin')):
        b = np.fromfile(f, dtype=np.uint8); n = len(b) // 520; r = b[:n * 520].reshape(n, 520)
        ids = r[:, :4].copy().view('<u4')[:, 0]; sc = r[:, 4:8].copy().view('<f4')[:, 0]
        v = r[:, 8:].view(np.int8).astype(np.float32) * sc[:, None]
        for i in range(n):
            e = L['p'].get(str(ids[i]))
            if sc[i] > 0 and e: X.append(v[i]); meta.append((e[1], L['groups'].get(str(e[3]), '') + ' ' + str(e[2]), lst)); lists.append(lst)
X = np.array(X); X /= np.linalg.norm(X, axis=1, keepdims=True); lists = np.array(lists)
Q = json.load(open('pockets.json'))
want = {'1': 'moltres & zapdos', '2': 'moltres & zapdos', '3': 'moltres & zapdos', '4': 'moltres & zapdos', '5': 'moltres & zapdos', '9': 'articuno', '10': 'zapdos', '11': 'moltres', '12': 'ho-oh'}
gm = X.mean(0); mu = {l: X[lists == l].mean(0) for l in np.unique(lists)}
for name in ('raw', 'list style removed', 'no Chinese'):
    top1 = 0; top8 = 0; lines = []
    for k, q in Q.items():
        q = np.array(q, np.float32); s = X @ q
        if name == 'list style removed':
            for l, m in mu.items(): s[lists == l] -= q @ (m - gm)
        if name == 'no Chinese': s[lists == 'pokemon-zh'] = -9
        order = np.argsort(-s)[:8]; names = [meta[i][0].lower() for i in order]
        a = want[k] in names[0]; b = any(want[k] in n for n in names); top1 += a; top8 += b
        lines.append(f'   {k}: {"OK " if a else ("in 8" if b else "no  ")} ' + ' | '.join(f'{meta[i][0]} [{meta[i][1]} {meta[i][2][8:]}] {s[i]:.3f}' for i in order[:3]))
    print(f'== {name}: right Pokémon first in {top1} of 9, among the 8 closest in {top8} of 9'); print('\n'.join(lines))

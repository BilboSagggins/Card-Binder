import os, glob, numpy as np, time
rows = []
for f in glob.glob('emb/*/*.bin'):
    b = np.fromfile(f, dtype=np.uint8)
    n = len(b) // 520; r = b[:n * 520].reshape(n, 520)
    sc = r[:, 4:8].copy().view(np.float32)[:, 0]
    v = r[:, 8:].view(np.int8).astype(np.float32) * sc[:, None]
    rows.append(v[sc > 0])
X = np.concatenate(rows); X /= np.linalg.norm(X, axis=1, keepdims=True)
print('cards', X.shape)
rng = np.random.default_rng(0)
m = X.mean(0); S = X[rng.choice(len(X), 20000, replace=False)] - m
_, sv, Vt = np.linalg.svd(S, full_matrices=False)
print('variance kept: 32 %.2f  64 %.2f  96 %.2f  128 %.2f' % tuple((sv[:k] ** 2).sum() / (sv ** 2).sum() for k in (32, 64, 96, 128)))
# queries: card fingerprints bent away until they sit at about 0.85 from the card (like a photographed pocket)
qi = rng.choice(len(X), 1500, replace=False)
noise = rng.standard_normal((1500, 512)).astype(np.float32); noise /= np.linalg.norm(noise, axis=1, keepdims=True)
for target in (0.85, 0.8):
    a = target; Q = a * X[qi] + np.sqrt(1 - a * a) * noise; Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    true = (Q @ X.T).argmax(1)
    for k in (64, 96, 128):
        P = Vt[:k]; C = (X - m) @ P.T
        sc = np.abs(C).max(0) / 127; Cq = np.round(C / sc).astype(np.int8)
        approx = (Q @ P.T * sc) @ Cq.T.astype(np.float32)
        order = np.argsort(-approx, axis=1)
        for top in (20, 50):
            hit = np.mean([true[i] in order[i, :top] for i in range(len(qi))])
            print(f'pocket~{target}: {k} dims, top {top}: right card found {hit*100:.1f}%  (file {len(X)*(k+7)/1048576:.1f} MB)')

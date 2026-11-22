import subprocess, os
r = subprocess.run('echo \'{"name":"emb","private":true}\' > package.json && npm i --no-audit --no-fund --onnxruntime-node-install-cuda=skip @huggingface/transformers@3.5.1 2>&1 | tail -2', shell=True, capture_output=True, text=True); print(r.stdout[-300:])
src = open('scripts/build-embeddings.mjs').read().replace("const LISTS = ['onepiece', 'pokemon', 'pokemon-jp'];", "const LISTS = ['onepiece'];")
open('scripts/build-embeddings.mjs', 'w').write(src)
r = subprocess.run(['node', 'scripts/build-embeddings.mjs'], capture_output=True, text=True, env={**os.environ, 'BUDGET_MIN': '2'}); print(r.stdout[-2500:]); print(r.stderr[-1500:])
r = subprocess.run(['node', 'scripts/emb-check.mjs'], capture_output=True, text=True); print(r.stdout[-2500:]); print(r.stderr[-1000:])

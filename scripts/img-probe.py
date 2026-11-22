import subprocess, os
r = subprocess.run('echo \'{"name":"emb","private":true}\' > package.json && npm i --no-audit --no-fund --onnxruntime-node-install-cuda=skip @huggingface/transformers@3.5.1 2>&1 | tail -1', shell=True, capture_output=True, text=True); print(r.stdout[-200:])
r = subprocess.run(['node', 'scripts/acc.mjs'], capture_output=True, text=True); print(r.stdout[-6000:]); print(r.stderr[-1500:])

import subprocess
r = subprocess.run('echo \'{"name":"emb","private":true}\' > package.json && npm i --no-audit --no-fund --onnxruntime-node-install-cuda=skip @huggingface/transformers@3.5.1 2>&1 | tail -1', shell=True, capture_output=True, text=True)
r = subprocess.run(['node', 'scripts/acc2.mjs'], capture_output=True, text=True); print(r.stdout[-3000:]); print(r.stderr[-800:])

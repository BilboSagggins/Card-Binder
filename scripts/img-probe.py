import subprocess
print(subprocess.run('git fetch -q origin main && git checkout origin/main -- emb && echo \'{"name":"emb","private":true}\' > package.json && npm i --no-audit --no-fund --onnxruntime-node-install-cuda=skip @huggingface/transformers@3.5.1 2>&1 | tail -1', shell=True, capture_output=True, text=True).stdout[-200:])
r = subprocess.run(['node', 'scripts/hub.mjs'], capture_output=True, text=True); print(r.stdout[-9000:]); print(r.stderr[-1500:])
subprocess.run('git rm -rq --cached emb; rm -rf emb', shell=True)

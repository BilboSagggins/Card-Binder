import subprocess, os
os.makedirs('/tmp/emb', exist_ok=True)
r = subprocess.run('cd /tmp/emb && echo "{\\"name\\":\\"emb\\",\\"private\\":true,\\"type\\":\\"module\\"}" > package.json && npm i --no-audit --no-fund @huggingface/transformers@3.5.1 2>&1 | grep -v "^npm error   " | tail -25; echo npm $?', shell=True, capture_output=True, text=True); print(r.stdout[-1500:], r.stderr[-500:])
subprocess.run(['cp', 'scripts/emb-test.mjs', '/tmp/emb/'])
for dt in []:
    r = subprocess.run(['node', '/tmp/emb/emb-test.mjs'], capture_output=True, text=True, env={**os.environ, 'DT': dt}, cwd=os.getcwd())
    print('DTYPE', dt); print(r.stdout[-1500:]); print(r.stderr[-800:])

import subprocess, os
print(subprocess.run('cd /tmp && npm init -y >/dev/null && npm i @huggingface/transformers@3.5.1 >/dev/null 2>&1; echo npm $?; nproc', shell=True, capture_output=True, text=True).stdout)
for dt in ['fp32', 'fp16']:
    r = subprocess.run(['node', os.path.abspath('scripts/emb-test.mjs')], capture_output=True, text=True, env={**os.environ, 'NODE_PATH': '/tmp/node_modules', 'DT': dt}, cwd=os.getcwd())
    print('DTYPE', dt); print(r.stdout[-1500:]); print(r.stderr[-1500:])

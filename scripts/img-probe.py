import subprocess, os
print(subprocess.run('npm init -y >/dev/null && npm i --no-save @huggingface/transformers@3.5.1 >/dev/null 2>&1; echo npm $?; nproc', shell=True, capture_output=True, text=True).stdout)
for dt in ['fp32', 'fp16']:
    r = subprocess.run(['node', 'scripts/emb-test.mjs'], capture_output=True, text=True, env={**os.environ, 'DT': dt})
    print('DTYPE', dt); print(r.stdout[-1500:]); print(r.stderr[-800:])

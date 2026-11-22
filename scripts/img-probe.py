import subprocess
print(subprocess.run('git fetch -q origin main && git checkout origin/main -- emb && pip install -q numpy 2>&1 | tail -1; echo ok', shell=True, capture_output=True, text=True).stdout)
r = subprocess.run(['python3', 'scripts/pca_test.py'], capture_output=True, text=True); print(r.stdout[-4000:]); print(r.stderr[-1500:])
subprocess.run('git rm -rq --cached emb; rm -rf emb', shell=True)
# run 1795377477

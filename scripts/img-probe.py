import subprocess
print(subprocess.run('pip install -q playwright 2>&1 | tail -1; python3 -m playwright install --with-deps chromium >/dev/null 2>&1; echo ok', shell=True, capture_output=True, text=True).stdout)
r = subprocess.run(['python3', 'scripts/photo_e2e.py'], capture_output=True, text=True); print(r.stdout[-6000:]); print(r.stderr[-2500:])

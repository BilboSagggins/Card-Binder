import subprocess, sys
r = subprocess.run([sys.executable, 'scripts/build-shops.py'], capture_output=True, text=True)
print(r.stdout[-3000:]); print('STDERR', r.stderr[-2000:])
print('=====JSON=====')
print(open('shops/cardquest.json').read())

import subprocess, sys
r = subprocess.run([sys.executable, 'scripts/build-shops.py'], capture_output=True, text=True)
print(r.stdout[-2500:]); print('STDERR', r.stderr[-1500:])
print('=====JSON=====')
print(open('shops/tradingcardworld.json').read())

import urllib.request, re, html, json, time
UA={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1','Accept':'*/*','HX-Request':'true'}
def get(u):
    try:
        t=time.time(); r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90); b=r.read().decode('utf-8','replace'); print(f'== {u[:150]} -> {r.status} len={len(b)} {time.time()-t:.1f}s', flush=True); return b
    except Exception as e: print(f'== {u} -> ERR {e}'); return ''
def items(b): return len(re.findall(r"data-variants='", b))
a=get('https://cardquestlgs.com/advanced-search-pokemon')
for nm in ['game']:
    print('game inputs:', re.findall(r'<(?:input|option|select)[^>]*name="game"[^>]*>', a)[:5])
print('game values in page:', sorted(set(re.findall(r'game[=:]["\']?([a-z_-]+)', a)))[:30])
s=get('https://cardquestlgs.com/search?q=luffy')
print('search more links:', re.findall(r'hx-get="(/search/more[^"]*)"', s)[:3])
print('luffy set/game hints:', sorted(set(re.findall(r'game[=:]["\']?([a-z_-]+)', s)))[:20])
for g in ['onepiece','one-piece','one_piece','optcg']:
    b=get(f'https://cardquestlgs.com/api/advanced-search?initialLoad=true&game={g}&inStockOnly=true&limit=20&offset=0')
    print(g, items(b), re.findall(r'productTitle"[^>]*>\s*([^<]+?)\s*<', b)[:3])
# size of pokemon in-stock with big pages
total=0
for off in range(0, 20000, 500):
    b=get(f'https://cardquestlgs.com/api/advanced-search?initialLoad=true&game=pokemon&inStockOnly=true&limit=500&offset={off}')
    n=items(b); total+=n; print('offset', off, 'items', n)
    if n<500: break
    time.sleep(1.5)
print('POKEMON IN STOCK TOTAL', total)

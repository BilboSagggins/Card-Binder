import urllib.request, json, time
UA={'User-Agent':'Mozilla/5.0 (compatible; CardBinderNeedList/1.0)','Accept':'application/json,*/*'}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60); b=r.read().decode('utf-8','replace'); print(f'== {u} -> {r.status} len={len(b)}'); return b
    except Exception as e: print(f'== {u} -> ERR {e}'); return ''
rb=get('https://tradingcardworld.store/robots.txt'); print('\n'.join(l for l in rb.splitlines() if l.strip() and not l.startswith('#'))[:1500])
for col in ['pokemon-singles','one-piece-singles']:
    b=get(f'https://tradingcardworld.store/collections/{col}/products.json?limit=250&page=1')
    try: d=json.loads(b)['products']
    except Exception as e: print('json err', e, b[:300]); continue
    print(col, 'page1 products', len(d))
    for p in d[:6]:
        print('  ', p['title'], '| type', p.get('product_type'), '| tags', p.get('tags')[:6] if isinstance(p.get('tags'),list) else p.get('tags'), '| handle', p['handle'])
        for v in p['variants'][:6]: print('      ', v['title'], v['price'], 'avail', v['available'], {k:v.get(k) for k in ('option1','option2','sku') })
    avail=sum(1 for p in d if any(v['available'] for v in p['variants'])); print('  in stock on page1:', avail)
    print('  key sample:', list(d[0].keys()), list(d[0]['variants'][0].keys()))
    time.sleep(2)

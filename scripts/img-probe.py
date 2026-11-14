import urllib.request, json, time, re, collections
UA={'User-Agent':'Mozilla/5.0 (compatible; CardBinderNeedList/1.0)','Accept':'application/json,*/*'}
def get(u):
    r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60); return r.read().decode('utf-8','replace')
for col in ['one-piece-singles','pokemon-singles']:
    allp=[]
    for page in range(1,40):
        d=json.loads(get(f'https://tradingcardworld.store/collections/{col}/products.json?limit=250&page={page}'))['products']
        allp+=d
        if len(d)<250: break
        time.sleep(2)
    inst=[p for p in allp if any(v['available'] for v in p['variants'])]
    print(col,'products',len(allp),'in stock',len(inst),'pages',page)
    opts=collections.Counter(v['title'] for p in inst for v in p['variants'] if v['available'])
    print('  variant titles:', opts.most_common(15))
    for p in inst[:10]:
        print('  ', p['title'], '| sku', p['variants'][0].get('sku'), '| body', re.sub(r'<[^>]+>',' ',p.get('body_html') or '')[:200].replace('\n',' '))
    nonum=[p['title'] for p in inst if not re.search(r'\(([^()]*\d[^()]*)\)\s*\[', p['title'])]
    print('  titles without number-ish paren:', len(nonum), nonum[:8])
    json.dump(inst, open(f'/tmp/{col}.json','w'))

import urllib.request, re, html, json, time
UA={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1','Accept':'*/*','HX-Request':'true'}
def get(u):
    try:
        t=time.time(); r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60); b=r.read().decode('utf-8','replace'); print(f'== {u} -> {r.status} len={len(b)} {time.time()-t:.1f}s'); return b
    except Exception as e: print(f'== {u} -> ERR {e}'); return ''
def parse(b):
    out=[]
    for m in re.finditer(r"data-variants='([^']*)'", b):
        seg=b[m.end():m.end()+4000]
        href=re.search(r'href="(/products/[^"]+)"', seg); t=re.search(r'productTitle"[^>]*>\s*([^<]+?)\s*</h2>', seg); sub=re.search(r'productSubtitle"[^>]*>([^<]*)<', seg)
        try: vs=json.loads(html.unescape(m.group(1)))
        except Exception as e: vs=[]; print('json err', e)
        out.append((href and href.group(1), t and html.unescape(t.group(1)), sub and html.unescape(sub.group(1)), [(v['title'], v['price'], v['inventory_quantity']) for v in vs if v.get('inventory_quantity',0)>0]))
    return out
b=get('https://cardquestlgs.com/search?q=charizard')
print('data-attrs near product:', sorted(set(re.findall(r'(data-[a-z-]+)=', b)))[:50])
for x in parse(b)[:6]: print(x)
for q in ['game=pokemon&inStockOnly=true&limit=100&offset=0&orderBy=price-desc', 'game=pokemon&inStockOnly=true&limit=100&offset=100&orderBy=price-desc', 'inStockOnly=true&limit=100&offset=0']:
    a=get('https://cardquestlgs.com/api/advanced-search?initialLoad=true&'+q)
    p=parse(a); print('items', len(p), 'links', len(set(re.findall(r'/products/product_\w+', a))))
    for x in p[:5]: print('  ', x)
    print('  totals text:', re.findall(r'(?i)(\d[\d,]*)\s*(?:results|products|items|of)', a)[:8], re.findall(r'(?i)offset=\d+[^"\']*', a)[:3])
for g in ['onepiece','one-piece','one_piece']:
    a=get(f'https://cardquestlgs.com/search?q=luffy'); print('luffy items', len(parse(a)), [x[1:3] for x in parse(a)[:5]]); break

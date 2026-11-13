import urllib.request, re, json, sys
UA={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1','Accept':'*/*'}
def get(u, n=4000, show=True):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30); b=r.read().decode('utf-8','replace')
        print(f'== {u} -> {r.status} {r.headers.get("content-type")} len={len(b)}')
        if show: print(b[:n])
        return b
    except Exception as e: print(f'== {u} -> ERR {e}'); return ''
home=get('https://cardquestlgs.com/', 0, False)
print('scripts:', re.findall(r'<script[^>]*src="([^"]+)"', home)[:30])
print('next data?', '__NEXT_DATA__' in home, 'nuxt' in home.lower())
for m in re.findall(r'https?://[a-z0-9.-]*shadowpos[a-z0-9./_-]*', home)[:20]: print('sp url:', m)
print('links:', sorted(set(re.findall(r'href="(/[^"#?]*)', home)))[:80])
s=get('https://cardquestlgs.com/advanced-search-pokemon?inStockOnly=true&orderBy=price-desc', 0, False)
print('adv scripts:', re.findall(r'<script[^>]*src="([^"]+)"', s)[:30])
i=s.find('Umbreon'); print('adv snippet:', s[:1500])
print('---- product cards in adv search:', len(re.findall(r'/products/product_', s)))
for js in re.findall(r'<script[^>]*src="([^"]+)"', s)[:12]:
    u = js if js.startswith('http') else 'https://cardquestlgs.com'+js
    b=get(u,0,False)
    for m in sorted(set(re.findall(r'["\'`](/api/[^"\'`]{2,80}|https://[a-z0-9.-]*(?:api|shadowpos)[^"\'`]{0,100})["\'`]', b)))[:40]: print('  endpoint in', js[-40:], ':', m)
for u in ['https://cardquestlgs.com/products.json','https://cardquestlgs.com/collections/pokemon-singles','https://cardquestlgs.com/sitemap.xml','https://cardquestlgs.com/robots.txt','https://cardquestlgs.com/search?q=charizard']:
    get(u, 1500)

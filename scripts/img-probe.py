import urllib.request, re, html
UA={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1','Accept':'*/*'}
def get(u, hx=False):
    h=dict(UA); 
    if hx: h['HX-Request']='true'
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=30); b=r.read().decode('utf-8','replace'); print(f'== {u} -> {r.status} len={len(b)}'); return b
    except Exception as e: print(f'== {u} -> ERR {e}'); return ''
s=get('https://cardquestlgs.com/search?q=charizard')
print('hx attrs:', sorted(set(re.findall(r'hx-(?:get|post)="([^"]+)"', s)))[:40])
i=s.find('/products/product_'); body=s[s.find('<main') if '<main' in s else 0:]
j=body.find('/products/product_')
print('---- first product snippet ----'); print(re.sub(r'\n\s*\n+','\n',body[max(0,j-1500):j+3500]))
print('product links:', len(set(re.findall(r'/products/product_\w+', s))))
a=get('https://cardquestlgs.com/advanced-search-pokemon?inStockOnly=true&orderBy=price-desc')
print('adv hx attrs:', sorted(set(re.findall(r'hx-(?:get|post|trigger|target)="([^"]+)"', a)))[:60])
print('adv forms:', re.findall(r'<form[^>]*>', a)[:5])
print('adv selects names:', sorted(set(re.findall(r'name="([^"]+)"', a)))[:60])
sm=get('https://cardquestlgs.com/sitemap/products.xml?cursor=0000c2eb-6a53-5add-9e4d-4caaa730f23d')
print(sm[:1500]); print('locs:', sm.count('<loc>'))

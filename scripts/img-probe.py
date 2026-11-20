import urllib.request, re, time
UA={'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1','Accept':'*/*','HX-Request':'true'}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60); b=r.read().decode('utf-8','replace'); return r.status,b
    except Exception as e: return str(e),''
base='https://cardquestlgs.com/api/advanced-search?initialLoad=true&game=pokemon&inStockOnly=true'
for q in ['&limit=500&offset=0&orderBy=price-desc','&limit=100&offset=0&orderBy=price-desc','&limit=50&offset=0','&limit=24&offset=0','&limit=20&offset=0','&offset=20','&limit=20&offset=20&orderBy=price-desc','&page=2','&limit=48']:
    st,b=get(base+q); n=len(re.findall(r"data-variants='",b))
    first=re.findall(r'productTitle"[^>]*>\s*([^<]+?)\s*<',b)[:2]
    print(q,'->',st,'items',n,first,'| more links:',re.findall(r'hx-get="(/api/advanced-search[^"]*)"',b)[:2], re.findall(r'(?i)(\d[\d,]*)\s+(?:results|products)',b)[:2])
    time.sleep(1.5)
st,b=get('https://cardquestlgs.com/advanced-search-pokemon')
print('page form inputs:', sorted(set(re.findall(r'name="(limit|offset|page|perPage|pageSize)"[^>]*value="([^"]*)"',b))))
print('limit options:', re.findall(r'<option[^>]*value="(\d+)"[^>]*>\s*\d+\s*(?:per|/)',b)[:10])

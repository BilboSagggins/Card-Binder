import urllib.request, json
UA={'User-Agent':'CardBinder/1.0'}
d=json.loads(urllib.request.urlopen(urllib.request.Request('https://pokeapi.co/api/v2/pokemon-species?limit=2000',headers=UA),timeout=60).read())
rows=[]
for r in d['results']:
    n=int(r['url'].rstrip('/').split('/')[-1]); rows.append((n,r['name']))
rows.sort(); print(len(rows)); print(json.dumps([n for _,n in rows]))

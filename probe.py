import urllib.request, json, re, html
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode('utf-8', 'replace')
out = []
def sec(t): out.append("\n######## " + t)
for cat in (3, 68, 80, 27, 89, 93):
    sec(f"groups cat {cat}")
    g = json.loads(get(f"https://tcgcsv.com/tcgplayer/{cat}/groups"))['results']
    g.sort(key=lambda x: x.get('publishedOn') or '', reverse=True)
    for x in g[:9]: out.append(f"  {x['groupId']} {x.get('publishedOn','')[:10]} {x.get('abbreviation')} | {x['name']} | sup={x.get('isSupplemental')}")
    if cat in (89, 3):
        for x in g[:2]:
            ps = json.loads(get(f"https://tcgcsv.com/tcgplayer/{cat}/{x['groupId']}/products"))['results']
            out.append(f"  -- products in {x['name']}: {len(ps)}")
            sealed = [p for p in ps if not any(e.get('name') == 'Number' for e in p.get('extendedData', []))]
            for p in sealed[:8]: out.append("   S " + json.dumps({k: p.get(k) for k in ('productId','name','imageUrl','url','presaleInfo','modifiedOn')})[:400])
            for p in ps[:1]: out.append("   P " + json.dumps(p)[:900])
sec("riftbound news")
t = get("https://riftbound.leagueoflegends.com/en-us/news/")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
if m:
    s = m.group(1); out.append("  next len %d" % len(s))
    for k in re.finditer(r'"title":"([^"]{5,140})"', s):
        out.append("   t " + k.group(1));
        if len(out) > 400: break
    i = s.find('"publishedAt"'); out.append("  sample: " + s[max(0,i-1500):i+600])
links = sorted(set(re.findall(r'href="(/en-us/news/[^"]+)"', t)))[:15]; out.append("  links " + " ".join(links))
sec("one piece topics")
t = get("https://en.onepiece-cardgame.com/topics/")
i = t.find('topics/'); j = t.find('<main'); 
for m in list(re.finditer(r'<a[^>]+href="([^"]*topics/[^"]+)"[^>]*>(.*?)</a>', t, re.S))[:6]:
    out.append("  A " + m.group(1) + " :: " + re.sub(r'\s+', ' ', m.group(2))[:400])
sec("bandai feed item")
t = get("https://shop.bandainamco-am.com/feed/")
items = re.findall(r'<item>(.*?)</item>', t, re.S)
for it in items[:8]: out.append("  T " + re.search(r'<title>(.*?)</title>', it, re.S).group(1) + " | " + (re.search(r'<pubDate>(.*?)</pubDate>', it) or [None,''])[1] + " | cats " + ",".join(re.findall(r'<category><!\[CDATA\[(.*?)\]\]>', it)))
eb = [it for it in items if 'EB-05 Release Event Information' in it]
if eb: out.append("  EB05 content: " + eb[0][:6000])
sec("pokebeach item")
t = get("https://www.pokebeach.com/forums/forums/front-page-news.18/index.rss")
it = re.findall(r'<item>(.*?)</item>', t, re.S)[0]; out.append(it[:3000])
sec("google item")
t = get("https://news.google.com/rss/search?q=%22Riftbound%22&hl=en-US&gl=US&ceid=US:en")
for it in re.findall(r'<item>(.*?)</item>', t, re.S)[:3]: out.append(it[:1200])
open('probe-report.txt', 'w').write("\n".join(out))

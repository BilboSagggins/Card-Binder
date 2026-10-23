import urllib.request, json, re, sys
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
urls = sys.argv[1:] or open('urls.txt').read().split()
out = []
def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r: return r.status, r.headers.get('content-type'), r.read()
for u in urls:
    try:
        st, ct, b = get(u); t = b.decode('utf-8', 'replace')
        out.append(f"=== {u}\nstatus {st} {ct} len {len(b)}")
        if 'categories' in u and 'tcgcsv' in u:
            for c in json.loads(t)['results']:
                if re.search(r'pok|one piece|dragon|riftbound|naruto|digimon|gundam|union', c['name'], re.I): out.append(f"  cat {c['categoryId']} {c['name']}")
        else:
            titles = re.findall(r'<title[^>]*>(.*?)</title>', t, re.S)[:8]
            og = re.findall(r'property="og:image" content="([^"]+)"', t)[:1]
            out.append("  titles: " + " || ".join(x.strip()[:110] for x in titles))
            if og: out.append("  og:image " + og[0])
            out.append("  head: " + re.sub(r'\s+', ' ', t[:900]))
    except Exception as e:
        out.append(f"=== {u}\nERROR {type(e).__name__}: {str(e)[:200]}")
open('probe-report.txt', 'w').write("\n".join(out))

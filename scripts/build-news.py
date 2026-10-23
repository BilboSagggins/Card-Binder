import urllib.request
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
for u in ["https://www.pokebeach.com/news/2026/10/product_pack_kmqoi.jpg","https://www.pokebeach.com/news/2026/10/product_pack_kmqoi-103x200.jpg","https://www.pokebeach.com/news/2026/10/057-Mega-Lucario-Z-ex.jpg"]:
    for ref in (None, "https://example.com/"):
        h={"User-Agent":UA}; 
        if ref: h["Referer"]=ref
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=20) as r: print(u, ref, r.status, r.headers.get('content-type'), len(r.read()))
        except Exception as e: print(u, ref, "ERR", e)

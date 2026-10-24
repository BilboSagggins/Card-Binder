import urllib.request
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
urls = ["https://tcgplayer-cdn.tcgplayer.com/product/200353_in_1000x1000.jpg", "https://tcgplayer-cdn.tcgplayer.com/product/200353_200w.jpg",
        "https://product-images.tcgplayer.com/fit-in/437x610/200353.jpg", "https://assets.tcgdex.net/en/sm/sm12/143/high.webp", "https://assets.tcgdex.net/en/sm/sm12/143/low.webp",
        "https://images.pokemontcg.io/sm12/143_hires.png", "https://images.pokemontcg.io/sm12/143.png", "https://i.ytimg.com/vi/x0rJ5v2yDps/hqdefault.jpg",
        "https://en.onepiece-cardgame.com/images/cardlist/card/OP01-001.png", "https://www.pokebeach.com/news/2026/10/057-Mega-Lucario-Z-ex.jpg",
        "https://cardtrader.com/uploads/blueprints/image/12345/show_x.jpg", "https://raw.githubusercontent.com/BilboSagggins/Card-Binder/main/prices/pokemon.json",
        "https://cdn.tailwindcss.com/", "https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js", "https://fonts.googleapis.com/css2?family=Inter:wght@500&display=swap"]
out = []
for u in urls:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Origin": "https://bilbosagggins.github.io"})
        with urllib.request.urlopen(req, timeout=20) as r:
            b = r.read()
            out.append(f"{r.status} ACAO={r.headers.get('access-control-allow-origin')} type={r.headers.get('content-type')} len={len(b)} cache={r.headers.get('cache-control')} | {u}")
    except Exception as e:
        out.append(f"ERR {e} | {u}")
open("probe-report.txt", "w").write("\n".join(out))

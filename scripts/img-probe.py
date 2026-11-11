import subprocess
def get(url, *hdr):
    a = ["curl", "-s", "-o", "/dev/null", "-D", "-", "-w", "SIZE %{size_download} CODE %{http_code}\n", url]
    for h in hdr: a[1:1] = ["-H", h]
    out = subprocess.run(a, capture_output=True, text=True).stdout
    return " | ".join(l.strip() for l in out.splitlines() if l.lower().startswith(("access-control-allow-origin", "content-type", "size", "location", "cross-origin")))
base = "https://cardtrader.com/uploads/blueprints/image/"
for path in ["353723/moltres-zapdos-articuno-gx-gold-secret-rare-185-150-shining-synergy-set-c.png", "353723/show_moltres-zapdos-articuno-gx-gold-secret-rare-185-150-shining-synergy-set-c.png", "353449/moltres-zapdos-articuno-gx-ultra-rare-104-150-shining-synergy-set-c.png"]:
    print("==", path[:60])
    print("  plain             ", get(base + path))
    print("  from the site     ", get(base + path, "Referer: https://bilbosagggins.github.io/", "Origin: https://bilbosagggins.github.io", "Sec-Fetch-Mode: cors"))
    print("  img, no referrer  ", get(base + path, "Accept: image/avif,image/webp,image/*,*/*;q=0.8", "Sec-Fetch-Dest: image", "User-Agent: Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"))
    print("  www.              ", get(base.replace("://", "://www.") + path))

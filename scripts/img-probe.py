import subprocess
def get(url, *hdr):
    a = ["curl", "-s", "-o", "/dev/null", "-D", "-", "-w", "SIZE %{size_download} CODE %{http_code}\n", url]
    for h in hdr: a[1:1] = ["-H", h]
    out = subprocess.run(a, capture_output=True, text=True).stdout
    return " | ".join(l.strip() for l in out.splitlines() if l.lower().startswith(("access-control-allow-origin", "content-type", "size", "location", "cross-origin")))
base = "https://www.cardtrader.com/uploads/blueprints/image/"
path = "353723/moltres-zapdos-articuno-gx-gold-secret-rare-185-150-shining-synergy-set-c.png"
UA = "User-Agent: Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"
print("www plain                ", get(base + path))
print("www + site referrer      ", get(base + path, UA, "Referer: https://bilbosagggins.github.io/", "Sec-Fetch-Dest: image", "Sec-Fetch-Mode: no-cors", "Sec-Fetch-Site: cross-site"))
print("www + cors from site     ", get(base + path, UA, "Origin: https://bilbosagggins.github.io", "Sec-Fetch-Mode: cors", "Sec-Fetch-Site: cross-site"))
print("www + test-page referrer ", get(base + path, UA, "Referer: https://bilbosagggins.github.io/Card-Binder/", "Sec-Fetch-Dest: image"))
print("old host + site referrer ", get(base.replace("www.", "") + path, UA, "Referer: https://bilbosagggins.github.io/", "Sec-Fetch-Dest: image"))

#!/usr/bin/env python3
"""One-time check: do CardTrader's card pictures load when shown on another website?"""
import urllib.request
for u in ["https://cardtrader.com/uploads/blueprints/image/413041/show_413041-pikachu-017-103-30th-celebration-simplified-chinese.png",
          "https://cardtrader.com/uploads/blueprints/image/413041/413041-pikachu-017-103-30th-celebration-simplified-chinese.png"]:
    for ref in ("https://bilbosagggins.github.io/", None):
        h = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1", "Accept": "image/*"}
        if ref: h["Referer"] = ref
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=30) as r:
                print(r.status, r.headers.get("Content-Type"), len(r.read()), "bytes | referer:", bool(ref), "|", u.rsplit('/', 1)[1][:40])
        except Exception as e:
            print("FAIL", e, "| referer:", bool(ref))

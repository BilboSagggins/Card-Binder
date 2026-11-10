#!/bin/bash
# Builds the app's style file (tw.css) from the Tailwind classes used in the page, and stamps the file's fingerprint
# into the page's <link>, so phones fetch a new copy only when the styles really changed.
#   tools/build-css.sh [page=index.html] [out=tw.css]
# Run it after changing index.html (the "Styles" check on GitHub fails when tw.css is out of date).
# Needs Node (uses npx tailwindcss@3.4.17), or set TAILWIND_BIN to a standalone tailwindcss binary.
set -e
PAGE=${1:-index.html}; OUT=${2:-tw.css}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
python3 - "$PAGE" "$tmp" <<'PY'
import os, re, sys
page, tmp = sys.argv[1], sys.argv[2]
s = open(page, encoding="utf-8").read()
m = re.search(r'<style type="text/tailwindcss">(.*?)</style>', s, re.S)      # the page's own component classes (.btn, .field, ...)
open(os.path.join(tmp, "in.css"), "w").write("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n@layer components {\n" + (m.group(1) if m else "") + "\n}\n")
# same settings as tailwind.config in the page
open(os.path.join(tmp, "tailwind.config.js"), "w").write(
    "module.exports={darkMode:'class',content:[%r],theme:{extend:{fontFamily:{sans:['Inter','sans-serif'],display:['Cinzel','serif']}}}}" % os.path.abspath(page))
PY
if [ -n "$TAILWIND_BIN" ] && [ -x "$TAILWIND_BIN" ]; then TW="$TAILWIND_BIN"; else TW="npx --yes tailwindcss@3.4.17"; fi
$TW -c "$tmp/tailwind.config.js" -i "$tmp/in.css" -o "$OUT" --minify 2>/dev/null
h=$(sha1sum "$OUT" | cut -c1-10)
python3 - "$PAGE" "$h" <<'PY'
import re, sys
page, h = sys.argv[1], sys.argv[2]
s = open(page, encoding="utf-8").read()
t = re.sub(r'href="tw\.css\?h=[0-9a-f]*"', 'href="tw.css?h=%s"' % h, s, count=1)
if t != s: open(page, "w", encoding="utf-8").write(t)
PY
echo "built $OUT ($(wc -c < "$OUT") bytes, fingerprint $h)"

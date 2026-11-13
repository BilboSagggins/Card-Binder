#!/usr/bin/env python3
"""Builds shops/<shop>.json: the singles a local shop has in stock right now, for the binder app's Need list
("Card Quest has it"). Card Quest runs on ShadowPOS, whose advanced search returns pages of products with
every variant's condition, price and quantity. Twice a day, a handful of requests, one at a time."""
import html, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

SHOPS = {
    'cardquest': {'name': 'Card Quest', 'url': 'https://cardquestlgs.com', 'games': ['pokemon', 'onepiece']},
}
UA = {'User-Agent': 'Mozilla/5.0 (compatible; CardBinderNeedList/1.0; +https://bilbosagggins.github.io/Card-Binder/)',
      'Accept': 'text/html,*/*', 'HX-Request': 'true'}
PAGE = 500


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            print(f'  {url} failed ({e}), try {i + 1}', file=sys.stderr)
            time.sleep(10 * (i + 1))
    return None


TITLE = re.compile(r'productTitle"[^>]*>\s*([^<]+?)\s*</h2>')
SUB = re.compile(r'productSubtitle"[^>]*>([^<]*)<')
HREF = re.compile(r'href="(/products/[^"]+)"')


def parse(b):
    out = []
    for m in re.finditer(r"data-variants='([^']*)'", b):
        seg = b[m.end():m.end() + 5000]
        t, s, h = TITLE.search(seg), SUB.search(seg), HREF.search(seg)
        if not (t and h):
            continue
        try:
            vs = json.loads(html.unescape(m.group(1)))
        except Exception:
            continue
        title = html.unescape(t.group(1)).strip()
        sub = html.unescape(s.group(1)).strip() if s else ''
        stock = []
        for v in vs:
            q = v.get('inventory_quantity') or 0
            if q <= 0 or v.get('available') is False:
                continue
            opts = {o.get('name'): o.get('value') for o in (v.get('options') or [])}
            price = v.get('price')
            if not price:
                continue
            stock.append([opts.get('Condition') or v.get('title') or '', opts.get('Printing') or '', round(float(price), 2), int(q)])
        if not stock:
            continue
        # "Monkey.D.Luffy (OP17-079 — Alternate Art)", "Umbreon (41/147)", "Charizard UPC"
        mm = re.match(r'^(.*?)\s*\(([^()]*?)(?:\s+[—–-]\s+(.*))?\)\s*$', title)
        name, num, label = (mm.group(1), mm.group(2), mm.group(3) or '') if mm else (title, '', '')
        if not re.search(r'\d', num):            # "(Holo)"-style label, not a number
            name, num, label = (mm.group(1), '', mm.group(2)) if mm else (title, '', '')
        ja = 1 if re.search(r'\[japanese\]', sub, re.I) else 0
        out.append([name.strip(), num.strip(), label.strip(), re.sub(r'\s*\[japanese\]\s*', ' ', sub, flags=re.I).strip(), ja, h.group(1).split('/products/')[-1], stock])
    return out


def build(key, shop, old):
    games = {}
    for g in shop['games']:
        items, ok = [], True
        for off in range(0, 40000, PAGE):
            b = get(f"{shop['url']}/api/advanced-search?initialLoad=true&game={g}&inStockOnly=true&limit={PAGE}&offset={off}&orderBy=price-desc")
            if b is None:
                ok = False
                break
            n = len(re.findall(r"data-variants='", b))
            items += parse(b)
            print(f'{key} {g} offset {off}: {n} products, {len(items)} in stock so far')
            if n < PAGE:
                break
            time.sleep(3)
        if ok and items:
            games[g] = items
        elif old and old.get('games', {}).get(g):
            print(f'{key} {g}: keeping the last list (this run failed)')
            games[g] = old['games'][g]
        time.sleep(3)
    return games


def main():
    os.makedirs('shops', exist_ok=True)
    for key, shop in SHOPS.items():
        path = f'shops/{key}.json'
        try:
            old = json.load(open(path))
        except Exception:
            old = None
        games = build(key, shop, old)
        if not any(games.values()):
            print(f'{key}: nothing fetched, leaving the file alone')
            continue
        data = {'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'name': shop['name'], 'url': shop['url'],
                'fields': ['name', 'number', 'label', 'set', 'japanese', 'product', 'stock: [condition, printing, price, qty]'],
                'games': games}
        if old and old.get('games') == games:
            print(f'{key}: no stock changes')
            continue
        with open(path, 'w') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        print(f'{key}: wrote {path} ({os.path.getsize(path)} bytes): ' + ', '.join(f'{g} {len(v)}' for g, v in games.items()))


if __name__ == '__main__':
    main()

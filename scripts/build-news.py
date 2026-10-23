"""Build news/news.json for the binder app's News tab.

Three parts, refreshed a few times a day by .github/workflows/news.yml:
  releases  upcoming (and just-released) sets and sealed products, from TCGplayer's catalog via TCGCSV
  raffles   store lotteries / drawings with entry links and dates (Bandai Namco shops, Riftbound drawings, news)
  items     latest news and card previews (PokeBeach, official One Piece and Riftbound news, Google News per game)

Every source is optional: if one fails, the rest still build and the failure is noted in "errors".
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; card-binder-news; +https://github.com/BilboSagggins/Card-Binder)"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
OUT = os.path.join(os.path.dirname(__file__), "..", "news", "news.json")
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date()
errors = []

# game key -> (label, TCGCSV categories)
GAMES = {
    "pokemon": ("Pokémon", [3]),
    "pokemon-jp": ("Pokémon Japan", [85]),
    "onepiece": ("One Piece", [68]),
    "fusionworld": ("DB Fusion World", [80]),
    "dbmasters": ("DB Masters", [27]),
    "naruto": ("Naruto", [93]),
    "riftbound": ("Riftbound", [89]),
}


def get(url, browser=False, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA if browser else UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def get_json(url, **kw):
    return json.loads(get(url, **kw))


def iso(d):
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def rss_date(s):
    try:
        return email.utils.parsedate_to_datetime(s.strip())
    except Exception:
        return None


def text(s):
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape(s)).strip()


def tag(block, name):
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S)
    return m.group(1).strip() if m else ""


def rss_items(xml):
    return re.findall(r"<item>(.*?)</item>", xml, re.S)


RAFFLE_RE = re.compile(r"\b(lottery|lotteries|raffle|drawing|drawings|draw entry|sign[- ]?up|registration)\b", re.I)
PREVIEW_RE = re.compile(r"\b(reveal|revealed|reveals|preview|previews|spoiler|spoilers|first look|new cards?|card list|secret rares?|illustration rares?)\b", re.I)
RELEASE_RE = re.compile(r"\b(announce[ds]?|release[ds]?|launch(es|ed)?|pre-?orders?|coming|set|box|collection|bundle|starter deck|booster)\b", re.I)


def kind_of(title):
    if RAFFLE_RE.search(title) and not re.search(r"\b(errata|rules?)\b", title, re.I):
        return "raffle"
    if PREVIEW_RE.search(title):
        return "preview"
    if RELEASE_RE.search(title):
        return "release"
    return "news"


# ---------------------------------------------------------------- releases (TCGCSV)
def is_card(p):
    return any(e.get("name") == "Number" for e in p.get("extendedData", []))


SEALED_RE = re.compile(r"box|pack|deck|bundle|case|set\b|collection|kit|tin|display|blister|sleeve|binder|portfolio|premium|gift|chest|bag|playmat|vault|starter|elite|trainer|build|battle|ultra|special|tournament|package", re.I)


def presale_products(cat, groups, skip):
    """Pre-order products added to other groups (special collections, tins, premium boxes...), by group."""
    recent = [g for g in groups if g["groupId"] not in skip and (g.get("modifiedOn") or "")[:10] >= str(TODAY - dt.timedelta(days=30))]
    recent.sort(key=lambda g: g.get("modifiedOn") or "", reverse=True)
    found = {}
    for g in recent[:40]:
        try:
            prods = get_json(f"https://tcgcsv.com/tcgplayer/{cat}/{g['groupId']}/products")["results"]
        except Exception as e:
            errors.append(f"products {g['groupId']}: {e}")
            continue
        for p in prods:
            pi = p.get("presaleInfo") or {}
            rel = (pi.get("releasedOn") or "")[:10]
            if is_card(p) or not rel or rel < str(TODAY - dt.timedelta(days=7)) or not SEALED_RE.search(p["name"]):
                continue
            found.setdefault(g["groupId"], (g, []))[1].append([p["productId"], p["name"], rel])
    return found


def build_releases():
    out = []
    for game, (label, cats) in GAMES.items():
        for cat in cats:
            try:
                groups = get_json(f"https://tcgcsv.com/tcgplayer/{cat}/groups")["results"]
            except Exception as e:
                errors.append(f"groups {cat}: {e}")
                continue
            newest_ids = sorted((g["groupId"] for g in groups), reverse=True)[:30]
            done = set()
            for g in groups:
                pub = (g.get("publishedOn") or "")[:10]
                try:
                    pub_d = dt.date.fromisoformat(pub)
                except ValueError:
                    continue
                # an upcoming set, or one that came out in the last three weeks (old groups get re-dated, so only new ids)
                if not (pub_d >= TODAY - dt.timedelta(days=21) and g["groupId"] in newest_ids):
                    continue
                try:
                    prods = get_json(f"https://tcgcsv.com/tcgplayer/{cat}/{g['groupId']}/products")["results"]
                except Exception as e:
                    errors.append(f"products {g['groupId']}: {e}")
                    prods = []
                sealed = []
                for p in prods:
                    if is_card(p) or not SEALED_RE.search(p["name"]):
                        continue
                    rel = ((p.get("presaleInfo") or {}).get("releasedOn") or "")[:10] or pub
                    sealed.append([p["productId"], p["name"], rel])
                sealed.sort(key=lambda x: (x[2], x[1]))
                done.add(g["groupId"])
                out.append({
                    "game": game, "gid": g["groupId"], "set": g["name"], "abbr": g.get("abbreviation") or "",
                    "date": pub, "cards": sum(1 for p in prods if is_card(p)), "products": sealed[:40],
                    "url": "https://www.tcgplayer.com/search/all/product?q=" + urllib.parse.quote(g["name"]),
                })
            # special products on pre-order in other groups: one entry per product release date
            for gid, (g, prods) in presale_products(cat, groups, done).items():
                by_date = {}
                for pr in prods:
                    by_date.setdefault(pr[2], []).append(pr)
                for day, ps in by_date.items():
                    ps.sort(key=lambda x: x[1])
                    out.append({
                        "game": game, "gid": gid, "set": ps[0][1] if len(ps) == 1 else g["name"], "abbr": g.get("abbreviation") or "",
                        "date": day, "cards": 0, "products": ps[:40], "special": True,
                        "url": f"https://www.tcgplayer.com/product/{ps[0][0]}" if len(ps) == 1 else "https://www.tcgplayer.com/search/all/product?q=" + urllib.parse.quote(g["name"]),
                    })
    out.sort(key=lambda r: (r["date"], r["game"], r["set"]))
    return out


# ---------------------------------------------------------------- raffles
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def dates_in(s, year_hint=None):
    """All dates written as 10/16/2026, 10/16 or October 16(, 2026) in a piece of text, in order."""
    found = []
    y0 = year_hint or TODAY.year
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*[-–]\s*(\d{1,2})(?:st|nd|rd|th)?\b)?(?:,?\s+(\d{4}))?", s, re.I):
        try:
            if m.group(1):
                y = int(m.group(3)) if m.group(3) else y0
                y = y + 2000 if y < 100 else y
                d = dt.date(y, int(m.group(1)), int(m.group(2)))
            else:
                y = int(m.group(7)) if m.group(7) else y0
                d = dt.date(y, MONTHS[m.group(4).lower()[:3]], int(m.group(5)))
                if m.group(6):          # "August 14-17": a range in one month
                    found.append(d)
                    d = dt.date(y, d.month, int(m.group(6)))
            found.append(d)
        except ValueError:
            pass
    return found


def window(sentences, year_hint=None):
    """(opens, closes) of a drawing: the date right after open/begin/start/runs and the one right after close/end/until."""
    opens = closes = None
    # "Announced on August 3" / "Updated 8/12" are post dates, not the entry window
    sentences = [re.sub(r"\b(announced|updated|posted|published|edited)\b\s*(on)?\s*:?\s*([A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)", " ", x, flags=re.I) for x in sentences]
    blob = " \n ".join(sentences)
    for m in re.finditer(r"\b(opens?|opening|begins?|starts?|starting|goes live|live on|runs?|running|from)\b|\b(clos(?:es|ing|e)|ends?|ending|deadline|until|through)\b", blob, re.I):
        before = blob[max(0, m.start() - 70):m.start()]
        after = blob[m.end():m.end() + 45]
        lab = re.search(r"([A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)[^\n]{0,20}?:(?!\d)[^:\n]{0,45}$", before)
        right_after = re.match(r"\s*(?:on|:)?\s*(?:[A-Za-z]+day,?\s*)?(?:[A-Za-z]{3,9}\.?\s+\d|\d{1,2}/\d)", after)
        # "opens: October 27" (date after) or "February 3rd, 9AM PST: Registration ... Begins" (date before)
        next_label = re.match(r"\s*(?:[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)[^\n]{0,20}?:(?!\d)", after)
        use_before = lab and (not right_after or next_label)     # the date after belongs to the next "date: label" line
        ds = dates_in(lab.group(1), year_hint) if use_before else dates_in(after, year_hint)
        if not ds:
            continue
        if m.group(1):
            opens = opens or ds[0]
            if len(ds) > 1 and re.match(r"[^\n]{0,30}?\d\s*[-–]\s*\d", blob[m.end():m.end() + 45]):
                closes = closes or ds[1]          # "runs August 14-17"
        else:
            closes = closes or ds[0]
    if not opens:
        allds = sorted(d for x in sentences for d in dates_in(x, year_hint))
        opens = allds[0] if allds else None
    return (str(opens) if opens else "", str(closes) if closes and (not opens or closes >= opens) else "")


def bandai_shops():
    """Bandai Namco Amusement America shops (One Piece official shops, Cross Store...): lottery posts with entry links."""
    raffles, items = [], []
    try:
        xml = get("https://shop.bandainamco-am.com/feed/", browser=True)
    except Exception as e:
        errors.append(f"bandai feed: {e}")
        return raffles, items
    for it in rss_items(xml):
        title = text(tag(it, "title"))
        link = text(tag(it, "link"))
        when = rss_date(tag(it, "pubDate"))
        body = re.sub(r"<!\[CDATA\[|\]\]>", "", tag(it, "content:encoded"))
        plain = text(body)
        cats = " ".join(text(c) for c in re.findall(r"<category>(.*?)</category>", it, re.S))
        game = "onepiece" if re.search(r"one piece", title + " " + cats, re.I) else \
            "fusionworld" if re.search(r"fusion world|dragon ball", title + " " + cats, re.I) else \
            "naruto" if re.search(r"naruto", title + " " + cats, re.I) else None
        if not game:
            continue          # Gundam Base, store openings etc.
        if re.search(r"lottery|raffle|drawing|register in advance", plain, re.I):
            period = ""
            m = re.search(r"(?:Lottery\s+)?(?:Application|Entry|Registration)\s+Period\s*:?\s*(.{10,160}?)(?=\n\s*\n|👉|📍|Check |$)", plain, re.I | re.S)
            if m:
                period = re.sub(r"\s+", " ", m.group(1)).strip(" –-")
            ev = re.search(r"release period \(([^)]+)\)|event (?:date|period)s?\s*:?\s*([^\n.]{4,60})", plain, re.I)
            entries = []
            for a in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
                url = html.unescape(a.group(1))
                if "shop.bandainamco-am.com" in url and url.rstrip("/") == link.rstrip("/"):
                    continue
                if "first appeared on" in body[max(0, a.start() - 40):a.start()] or url.rstrip("/") == "https://shop.bandainamco-am.com":
                    continue
                # label: the place name just before the link ("📍 Plano, TX<br><a ...>")
                before = text(body[max(0, a.start() - 220):a.start()]).split("\n")[-1]
                before = re.sub(r"^.*?\)\s*", "", before) if len(before) > 60 else before
                label = text(a.group(2))
                if label.startswith("http"):
                    label = before.strip(" :📍👉") or "Enter"
                entries.append([label[:60], url])
            if re.search(r"\bfaq\b", title, re.I):
                items.append({"game": game, "title": title, "url": link, "date": iso(when), "src": "Bandai Namco Shops", "kind": "news", "imgs": []})
                continue
            pd = dates_in(period, when.year if when else None)
            raffles.append({
                "opens": str(pd[0]) if pd else "", "closes": str(pd[-1]) if pd else "",
                "game": game, "title": title, "url": link, "posted": iso(when), "src": "Bandai Namco Shops",
                "period": period, "event": (ev.group(1) or ev.group(2)).strip() if ev else "", "entries": entries[:20],
                "summary": plain[:280],
            })
        else:
            items.append({"game": game, "title": title, "url": link, "date": iso(when), "src": "Bandai Namco Shops", "kind": kind_of(title), "imgs": []})
    return raffles, items


# ---------------------------------------------------------------- news
def pokebeach():
    items = []
    try:
        xml = get("https://www.pokebeach.com/forums/forums/front-page-news.18/index.rss", browser=True)
    except Exception as e:
        errors.append(f"pokebeach: {e}")
        return items
    for it in rss_items(xml)[:40]:
        title = text(tag(it, "title"))
        body = tag(it, "content:encoded")
        imgs = [u for u in re.findall(r'<img[^>]+src="([^"]+)"', body) if "/news/" in u and "smilies" not in u]
        # thumbnails are named -WxH; the full image drops that suffix
        imgs = [re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u) for u in imgs][:8]
        game = "pokemon-jp" if re.search(r"\bjapan(ese)?\b", text(body)[:400], re.I) and not re.search(r"\benglish\b", title, re.I) else "pokemon"
        if re.search(r"\bpocket\b|\blive\b|video game|anime|movie", title, re.I) and not re.search(r"\bTCG\b", title):
            continue
        items.append({"game": game, "title": title, "url": text(tag(it, "link")), "date": iso(rss_date(tag(it, "pubDate"))),
                      "src": "PokeBeach", "kind": kind_of(title), "imgs": imgs, "summary": text(body)[:240]})
    return items


def onepiece_official():
    items = []
    try:
        page = get("https://en.onepiece-cardgame.com/topics/", browser=True)
    except Exception as e:
        errors.append(f"onepiece topics: {e}")
        return items
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]*topics/[^"?#]+\.php)"[^>]*>(.*?)</a>', page, re.S):
        href, inner = m.group(1), m.group(2)
        t = re.search(r'class="js_topicTit">(.*?)</span>', inner, re.S)
        if not t:
            continue
        title = text(t.group(1))
        if title in seen:
            continue
        seen.add(title)
        img = re.search(r'<img src="([^"]+)"', inner)
        d = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", inner)
        date = iso(dt.datetime(int(d.group(1)), int(d.group(2)), int(d.group(3)), 12, tzinfo=dt.timezone.utc)) if d else None
        url = urllib.parse.urljoin("https://en.onepiece-cardgame.com/topics/", href)
        imgs = [urllib.parse.urljoin("https://en.onepiece-cardgame.com/topics/", img.group(1))] if img and "common/thumbnail" not in img.group(1) else []
        items.append({"game": "onepiece", "title": title, "url": url, "date": date, "src": "One Piece Card Game (official)", "kind": kind_of(title), "imgs": imgs})
        if len(items) >= 15:
            break
    return items


def riftbound_official():
    raffles, items = [], []
    try:
        page = get("https://riftbound.leagueoflegends.com/en-us/news/", browser=True)
        data = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S).group(1))
    except Exception as e:
        errors.append(f"riftbound news: {e}")
        return raffles, items
    found = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("title"), str) and (o.get("publishedAt") or o.get("date")):
                url = (((o.get("action") or {}).get("payload") or {}).get("url")) or o.get("url") or ""
                img = ((o.get("media") or {}).get("url")) or ""
                found.append((o["title"], o.get("publishedAt") or o.get("date"), url, img, o.get("description") or ""))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    # text that sits on every page (e.g. a site-wide "Enter drawing for ..." banner): ignore it inside articles
    banner = set(sentences_of(page))
    seen = set()
    for title, when, url, img, desc in found:
        if title in seen:
            continue
        seen.add(title)
        url = urllib.parse.urljoin("https://riftbound.leagueoflegends.com/en-us/news/", url) if url else "https://riftbound.leagueoflegends.com/en-us/news/"
        try:
            d = dt.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
        except ValueError:
            d = None
        desc = text(desc if isinstance(desc, str) else json.dumps(desc))[:240]
        recent = d and d > NOW - dt.timedelta(days=60)
        named = RAFFLE_RE.search(title) and not re.search(r"\bfaq\b", title, re.I)
        maybe = re.search(r"collection|edition|signature|bundle|exclusive|limited|pre-?order|drawing|lottery|raffle", title + " " + desc, re.I) and not re.search(r"\bfaq\b", title, re.I)
        if recent and (named or maybe):
            r = riftbound_drawing(title, url, d, desc, banner)
            if named or r.pop("drawing", False):
                raffles.append(r)
        items.append({"game": "riftbound", "title": title, "url": url, "date": iso(d), "src": "Riftbound (official)",
                      "kind": kind_of(title), "imgs": [img.split("?")[0] + "?w=800"] if img else [], "summary": desc})
    return raffles, items[:20]


def sentences_of(page):
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    strings = re.findall(r'"(?:text|body|description|content|html|value|title|label)":"((?:[^"\\]|\\.){20,})"', nd.group(1) if nd else page)
    out = []
    for x in strings:
        try:
            x = json.loads('"' + x + '"')
        except ValueError:
            continue
        out += [y.strip() for y in re.split(r"(?<=[.!?])\s+|\n", text(x)) if len(y.strip()) > 12]
    return out


def riftbound_drawing(title, url, d, desc, banner=()):
    """Open a Riftbound article for drawing dates and entry links. Sets "drawing" when the article describes one."""
    r = {"game": "riftbound", "title": title, "url": url, "posted": iso(d), "src": "Riftbound (official)",
         "period": "", "event": "", "entries": [], "summary": desc}
    try:
        page = get(url, browser=True)
        nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        sents = [x for x in dict.fromkeys(sentences_of(page)) if x not in banner and re.search(r"draw|lottery|raffle|regist|sign up|selectees|winners?|purchase window", x, re.I)]
        dated = [x for x in sents if dates_in(x)]
        r["drawing"] = bool([x for x in dated if re.search(r"drawing|lottery|raffle|registration", x, re.I)])
        r["summary"] = " ".join((dated or sents)[:4])[:600] or desc
        for a in re.finditer(r'"(https?://[^"\s]+)"', nd.group(1) if nd else page):
            u = a.group(1).replace("\\u002F", "/").replace("\\/", "/").rstrip("\\")
            if re.search(r"draw|raffle|enter|form|regist|signup|sign-up|queue", u, re.I) and "cmsassets" not in u and not re.search(r"youtube|youtu\.be|twitter|x\.com|facebook|instagram|tiktok|discord|twitch|reddit|publishing-content|/api/|\.(js|json|css|png|jpe?g|webp)(\?|$)", u) and not re.search(r"(playriftbound|riftbound\.leagueoflegends)\.com/[a-z-]+/news/", u):
                if u not in [e[1] for e in r["entries"]]:
                    r["entries"].append([re.sub(r"^https?://(www\.)?", "", u).split("/")[0], u])
        r["opens"], r["closes"] = window(dated, d.year)
        # only a drawing if its dates are after the article went up (not an old date mentioned in passing)
        if r["drawing"] and not any(x and dt.date.fromisoformat(x) >= d.date() - dt.timedelta(days=2) for x in (r["opens"], r["closes"])):
            r["drawing"] = False
    except Exception as e:
        errors.append(f"riftbound drawing {url}: {e}")
    r["entries"] = r["entries"][:6] or [["Open the drawing page", url]]
    return r


# Official YouTube channels (the same reveal videos the publishers post on X, which can't be read without a paid API)
YOUTUBE = [
    ("UCT5u6XqA2oaSqxsXKp3zubw", "Bandai Card Games (official)", None),          # One Piece, Fusion World, DB Masters...
    ("UCZVYjENKJSXMke-dYUxCLvw", "NARUTO CARD GAME (official)", "naruto"),
    ("UCjrU2FHeEIQFP3GOcCOiuVw", "Riftbound (official)", "riftbound"),
    ("UCFctpiB_Hnlk3ejWfHqSm6Q", "Pokémon (official)", "pokemon"),               # TCG videos only (see below)
]
VIDEO_PREVIEW_RE = re.compile(r"reveal|preview|spoiler|new cards?|card list|trailer|\bPV\b|promotion video|introduc|showcase|first look|booster|starter deck|extra booster|premium|set\b|product|collection|leader|legend|champion|unbox|opening", re.I)
VIDEO_SKIP_RE = re.compile(r"\blive\b|stream|tournament|championship|\bfinals\b|grand final|top \d|regional|how to play|tutorial|\brules\b|gameplay|\bmatch\b|\bvs\.?\b|news!|quiz", re.I)


def bandai_game(title):
    if re.search(r"one ?piece", title, re.I):
        return "onepiece"
    if re.search(r"fusion ?world", title, re.I):
        return "fusionworld"
    if re.search(r"dragon ?ball", title, re.I):
        return "dbmasters"
    if re.search(r"naruto", title, re.I):
        return "naruto"
    return None          # Digimon, Gundam, Union Arena... not followed here


def youtube_videos():
    items = []
    for cid, src, game in YOUTUBE:
        try:
            xml = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", browser=True)
        except Exception as e:
            errors.append(f"youtube {src}: {e}")
            continue
        for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
            vid = tag(e, "yt:videoId")
            title = text(tag(e, "title"))
            g = game or bandai_game(title)
            if not vid or not g or VIDEO_SKIP_RE.search(title):
                continue
            if g == "pokemon" and not re.search(r"\bTCG\b|trading card", title, re.I):
                continue      # the main Pokémon channel: games, anime... only card game videos
            pub = tag(e, "published")
            try:
                when = dt.datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                when = None
            items.append({"game": g, "title": title, "url": f"https://www.youtube.com/watch?v={vid}", "date": iso(when), "src": src,
                          "kind": "preview", "imgs": [f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"], "video": vid})
    return items


GOOGLE = [
    ("pokemon", '"Pokemon TCG" OR "Pokémon TCG"'),
    ("onepiece", '"One Piece Card Game" OR "One Piece TCG"'),
    ("fusionworld", '"Fusion World" "Dragon Ball"'),
    ("dbmasters", '"Dragon Ball Super Card Game" Masters'),
    ("naruto", '"Naruto Card Game" OR "Naruto TCG"'),
    ("riftbound", 'Riftbound'),
    # drawings / lotteries get their own searches so they aren't crowded out by other news
    ("pokemon", '"Pokemon Center" OR "Pokémon TCG" (lottery OR raffle OR drawing)'),
    ("onepiece", '"One Piece Card Game" OR "One Piece TCG" (lottery OR raffle OR drawing)'),
    ("fusionworld", '"Fusion World" (lottery OR raffle OR drawing)'),
    ("naruto", '"Naruto Card Game" (lottery OR raffle OR drawing)'),
    ("riftbound", 'Riftbound (drawing OR lottery OR raffle)'),
]
DEAL_RE = re.compile(r"\bdeals?\b|\bsave\b|\bprice\b|discount|% off|under market|best-ever|\bon (amazon|walmart|target)\b|\bat (amazon|walmart|target)\b|restock", re.I)
CARDISH_RE = re.compile(r"card|tcg|booster|deck|\bpack|\bbox\b|promo|riftbound|\bset\b|collection|tournament|championship|prerelease|pre-rift", re.I)
SKIP_SRC = re.compile(r"reddit|youtube|facebook|instagram|tiktok|ebay|amazon|walmart|press release|einpresswire|globenewswire|prnewswire", re.I)


FAILED_GOOGLE = set()


def google_news():
    items = []
    for n, (game, q) in enumerate(GOOGLE):
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:30d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        xml = None
        for attempt in range(3):
            time.sleep(1.5 if n or attempt else 0)
            try:
                xml = get(url, browser=True)
                break
            except Exception as e:
                err = e
                time.sleep(6 * (attempt + 1))
        if xml is None:
            errors.append(f"google {game}: {err}")
            FAILED_GOOGLE.add(game)
            continue
        for it in rss_items(xml)[:25]:
            full = text(tag(it, "title"))
            src = text(tag(it, "source")) or (full.rsplit(" - ", 1)[1] if " - " in full else "")
            title = full.rsplit(" - ", 1)[0] if src and full.endswith(" - " + src) else full
            if SKIP_SRC.search(src) or "Pocket" in title and game == "pokemon" or DEAL_RE.search(title) or not CARDISH_RE.search(title + " " + src) \
                    or game in ("fusionworld", "dbmasters") and not re.search(r"card|tcg|fusion world|booster|masters", title, re.I):
                continue
            items.append({"game": game, "title": title, "url": text(tag(it, "link")), "date": iso(rss_date(tag(it, "pubDate"))),
                          "src": src, "kind": kind_of(title), "imgs": [], "via": "google"})
    return items


OFFICIAL_SRC = re.compile(r"^(Riftbound|League of Legends|Riot Games|Pok[eé]mon(\.com| Center| TCG)?|The Pok[eé]mon Company.*|One Piece Card Game.*|ONE PIECE CARD GAME.*|Bandai.*|BANDAI.*|Dragon Ball Super Card Game.*|DRAGON BALL SUPER CARD GAME.*|Naruto Card Game.*|NARUTO CARD GAME.*)$|\(official\)$|^Bandai Namco Shops$", re.I)


def merge_raffles(raffles):
    """One card per drawing: the same game with the same opening date is the same drawing (keep the most complete one)."""
    score = lambda r: (bool(r.get("closes")), len([e for e in r.get("entries", []) if e[0] != "Open the drawing page"]),
                       bool(re.search(r"drawing|lottery|raffle", r["title"], re.I)), len(r.get("summary", "")))
    best = {}
    for r in raffles:
        k = (r["game"], r.get("opens") or norm_title(r["title"]))
        if k not in best or score(r) > score(best[k]):
            best[k] = r
    return list(best.values())


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()[:70]


def main():
    data = {"updated": iso(NOW), "games": {k: v[0] for k, v in GAMES.items()}}
    try:
        data["releases"] = build_releases()
    except Exception as e:
        errors.append(f"releases: {e}")
        data["releases"] = []
    raffles, items = [], []
    r, i = bandai_shops(); raffles += r; items += i
    r, i = riftbound_official(); raffles += r; items += i
    items += pokebeach()
    items += onepiece_official()
    items += youtube_videos()
    items += google_news()
    # a Google search that failed this time: keep what the last run found for that game
    if FAILED_GOOGLE:
        try:
            with open(OUT, encoding="utf-8") as f:
                prev = json.load(f)
            items += [x for x in prev.get("items", []) if x.get("via") == "google" and x["game"] in FAILED_GOOGLE]
            raffles += [x for x in prev.get("raffles", []) if x.get("via") == "google" and x["game"] in FAILED_GOOGLE]
        except Exception as e:
            errors.append(f"previous news: {e}")
    # a drawing / lottery posted by the official publisher or store (found through news search) also goes on the raffle
    # list; drawings reported by other sites stay in the news only
    have = {norm_title(x["title"]) for x in raffles}
    for it in items:
        if it["kind"] == "raffle" and OFFICIAL_SRC.search(it.get("src", "")) and norm_title(it["title"]) not in have and it.get("date") and not re.search(r"\bfaq\b", it["title"], re.I) and \
                dt.datetime.fromisoformat(it["date"].replace("Z", "+00:00")) > NOW - dt.timedelta(days=45):
            posted = dt.datetime.fromisoformat(it["date"].replace("Z", "+00:00"))
            o, c = window([it["title"]] + re.split(r"(?<=[.!?])\s+", it.get("summary", "")), posted.year)
            if o and dt.date.fromisoformat(o) < posted.date() - dt.timedelta(days=2):
                o, c = "", ""       # a date from before the post: not the entry window
            raffles.append({"game": it["game"], "title": it["title"], "url": it["url"], "posted": it["date"], "src": it["src"], "via": it.get("via", ""),
                            "opens": o, "closes": c, "period": "", "event": "", "entries": [], "summary": it.get("summary", "")})
            have.add(norm_title(it["title"]))
    # newest first; drop near-duplicate headlines (keep the copy with pictures / from the official source)
    items.sort(key=lambda x: (bool(x["imgs"]), x.get("date") or ""), reverse=True)
    seen, uniq = set(), []
    for it in items:
        k = norm_title(it["title"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    cutoff = iso(NOW - dt.timedelta(days=60))
    uniq = [x for x in uniq if (x.get("date") or "") >= cutoff or x["src"].endswith("(official)")]
    uniq.sort(key=lambda x: x.get("date") or "", reverse=True)
    raffles = merge_raffles([r for r in raffles if OFFICIAL_SRC.search(r.get("src", ""))])
    raffles.sort(key=lambda x: x.get("posted") or "", reverse=True)
    data["raffles"] = raffles[:40]
    data["items"] = uniq[:250]
    data["errors"] = errors
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"releases {len(data['releases'])}, raffles {len(data['raffles'])}, items {len(data['items'])}, errors {len(errors)}")
    for e in errors:
        print("  !", e, file=sys.stderr)


if __name__ == "__main__":
    main()

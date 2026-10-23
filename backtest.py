"""Would the news job have caught the Riftbound T1 drawing earlier this year?"""
import importlib.util, re, urllib.parse, json
spec = importlib.util.spec_from_file_location("bn", "scripts/build-news.py"); bn = importlib.util.module_from_spec(spec); spec.loader.exec_module(bn)
out = []
def p(*a): out.append(" ".join(str(x) for x in a))
# 1) Google News, as the job queries it, but for the months around the T1 release (Aug 1)
for q in ['Riftbound', 'Riftbound T1', 'Riftbound drawing']:
    for a, b in [("2026-05-01", "2026-06-15"), ("2026-06-15", "2026-07-20"), ("2026-07-20", "2026-08-31")]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f"{q} after:{a} before:{b}", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        try: xml = bn.get(url, browser=True)
        except Exception as e: p("ERR", q, e); continue
        for it in bn.rss_items(xml):
            t = bn.text(bn.tag(it, "title"))
            if re.search(r"t1|worlds champion|drawing|raffle|lottery", t, re.I):
                p(f"[google '{q}' {a}..{b}]", (bn.rss_date(bn.tag(it, 'pubDate')) or '').__str__()[:10], "kind=" + bn.kind_of(t), "|", t)
# 2) Riftbound's official site: every news article in the sitemap that mentions T1 / drawing
urls = []
for sm in ["https://riftbound.leagueoflegends.com/sitemap.xml", "https://riftbound.leagueoflegends.com/en-us/sitemap.xml", "https://playriftbound.com/sitemap.xml"]:
    try:
        x = bn.get(sm, browser=True); locs = re.findall(r"<loc>(.*?)</loc>", x); p("sitemap", sm, len(locs))
        for l in locs:
            if l.endswith(".xml"):
                try: locs += re.findall(r"<loc>(.*?)</loc>", bn.get(l, browser=True))
                except Exception as e: p("  sub ERR", l, e)
        urls += [l for l in locs if "/news/" in l and re.search(r"t1|drawing|champion", l, re.I)]
    except Exception as e: p("sitemap ERR", sm, e)
urls = sorted(set(u for u in urls if "/en-us/" in u))
p("official T1/drawing articles:", len(urls)); [p("  ", u) for u in urls[:30]]
import datetime as dt
for u in urls[:12]:
    title = u.rstrip("/").split("/")[-1].replace("-", " ")
    p("\n== would-be raffle?", title, "| kind:", bn.kind_of(title), "| raffle-word:", bool(bn.RAFFLE_RE.search(title)))
    r = bn.riftbound_drawing(title, u, dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc), "")
    p("   opens", r.get("opens"), "closes", r.get("closes"), "| entries", r["entries"][:3]); p("   summary:", r["summary"][:500])
p("errors:", bn.errors)
open("probe-report.txt", "w").write("\n".join(out))

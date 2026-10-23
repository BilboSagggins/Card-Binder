"""Replay: what would the Raffles list have shown around the Riftbound T1 Signature Edition drawing (Aug 2026)?"""
import importlib.util, re, urllib.parse, datetime as dt
spec = importlib.util.spec_from_file_location("bn", "scripts/build-news.py"); bn = importlib.util.module_from_spec(spec); spec.loader.exec_module(bn)
out = []
def p(*a): out.append(" ".join(str(x) for x in a))
for day in ["2026-08-05", "2026-08-13", "2026-08-15"]:
    now = dt.datetime.fromisoformat(day + "T18:00:00+00:00"); bn.NOW, bn.TODAY = now, now.date()
    a = (now - dt.timedelta(days=30)).date()
    items = []
    xml = ""
    for q in [q for g, q in bn.GOOGLE if g == "riftbound"]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": f"{q} after:{a} before:{now.date() + dt.timedelta(days=1)}", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        xml += "".join("<item>" + x + "</item>" for x in bn.rss_items(bn.get(url, browser=True))[:25])
    seen = set()
    for it in bn.rss_items(xml):
        if bn.tag(it, "title") in seen: continue
        seen.add(bn.tag(it, "title"))
        full = bn.text(bn.tag(it, "title")); src = bn.text(bn.tag(it, "source"))
        title = full.rsplit(" - ", 1)[0] if src and full.endswith(" - " + src) else full
        if bn.SKIP_SRC.search(src) or bn.DEAL_RE.search(title) or not bn.CARDISH_RE.search(title + " " + src): continue
        items.append({"game": "riftbound", "title": title, "url": "", "date": bn.iso(bn.rss_date(bn.tag(it, "pubDate"))), "src": src, "kind": bn.kind_of(title), "summary": ""})
    p(f"\n=== As of {day}: Google News, the job's two Riftbound searches (past 30 days) -> {len(items)} items; raffle-type:")
    for it in items:
        if it["kind"] == "raffle" and not re.search(r"\bfaq\b", it["title"], re.I):
            posted = dt.datetime.fromisoformat(it["date"].replace("Z", "+00:00"))
            o, c = bn.window([it["title"]], posted.year)
            if o and dt.date.fromisoformat(o) < posted.date() - dt.timedelta(days=2): o, c = "", ""
            live = (c and now.date() <= dt.date.fromisoformat(c)) or (o and not c and (now.date() - dt.date.fromisoformat(o)).days <= 7) or (o and now.date() < dt.date.fromisoformat(o))
            p(f"   {it['date'][:10]} opens={o or '-'} closes={c or '-'} alert={'YES' if live else 'no'} | {it['title']} ({it['src']})")
# Riot's own T1 article, read with today's job
bn.NOW, bn.TODAY = dt.datetime.now(dt.timezone.utc), dt.date.today()
idx = bn.get("https://riftbound.leagueoflegends.com/en-us/news/", browser=True); banner = set(bn.sentences_of(idx))
u = "https://playriftbound.com/en-us/news/announcements/the-riftbound-x-t1-2025-worlds-champion-collection/"
r = bn.riftbound_drawing("The Riftbound x T1 2025 Worlds Champion Collection", u, dt.datetime(2026, 7, 2, tzinfo=dt.timezone.utc), "", banner)
p("\n=== Riot's T1 article:", "counts as a drawing:", r.get("drawing"), "| opens", r.get("opens"), "closes", r.get("closes"), "| entries", r["entries"][:3]); p("   summary:", r["summary"])
p("errors:", bn.errors)
open("probe-report.txt", "w").write("\n".join(out))

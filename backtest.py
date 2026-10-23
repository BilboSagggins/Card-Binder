import urllib.request, urllib.parse, re, json
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
out = []
def p(*a): out.append(" ".join(str(x) for x in a))
def get(u, h=None):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", **(h or {})})
    with urllib.request.urlopen(req, timeout=25) as r: return r.status, r.read().decode("utf-8", "replace")
handles = ["narutotcg_eng", "ONEPIECE_tcg_EN", "dbfw_cardgameEN", "dbs_cardgame", "playriftbound"]
p("#### X")
for h in handles[:2]:
    for u in [f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}", f"https://x.com/{h}", f"https://nitter.net/{h}/rss", f"https://rss.app/feeds/{h}"]:
        try:
            st, t = get(u); vids = len(re.findall(r'video\.twimg\.com|"video_info"|ext_tw_video', t)); tw = len(re.findall(r'"id_str"|/status/\d+', t))
            p(st, u, "len", len(t), "videos", vids, "tweets", tw, "|", re.sub(r"\s+", " ", t[:200]))
        except Exception as e: p("ERR", u, e)
p("#### official sites -> youtube links")
for site in ["https://en.onepiece-cardgame.com/", "https://www.dbs-cardgame.com/fw/en/", "https://www.dbs-cardgame.com/us-en/", "https://riftbound.leagueoflegends.com/en-us/", "https://www.narutocardgame.com/", "https://narutocardgame.com/en/", "https://www.naruto-cardgame.com/en/"]:
    try:
        st, t = get(site)
        yt = sorted(set(re.findall(r'https?://(?:www\.)?youtube\.com/(?:@[\w.-]+|channel/[\w-]+|c/[\w-]+|user/[\w-]+)', t)))
        xs = sorted(set(re.findall(r'https?://(?:www\.)?(?:x|twitter)\.com/[\w]+', t)))
        p(st, site, "youtube:", yt[:6], "x:", xs[:6])
    except Exception as e: p("ERR", site, e)
p("#### youtube search -> channels")
for q in ["ONE PIECE CARD GAME official", "Riftbound League of Legends TCG", "Dragon Ball Super Card Game Fusion World official", "Dragon Ball Super Card Game official", "NARUTO CARD GAME Bandai official"]:
    try:
        st, t = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&sp=EgIQAg%3D%3D")  # channels filter
        chans = re.findall(r'"channelId":"(UC[\w-]{22})","title":\{"simpleText":"([^"]+)"\}', t)
        handles2 = re.findall(r'"canonicalBaseUrl":"(/@[^"]+)"', t)
        subs = re.findall(r'"videoCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"', t)
        p(q, "->", list(dict.fromkeys(chans))[:5], list(dict.fromkeys(handles2))[:5])
    except Exception as e: p("ERR yt", q, e)
open("probe-report.txt", "w").write("\n".join(out))

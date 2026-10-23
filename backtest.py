import importlib.util
spec = importlib.util.spec_from_file_location("bn", "scripts/build-news.py"); bn = importlib.util.module_from_spec(spec); spec.loader.exec_module(bn)
out = []
v = bn.youtube_videos()
out.append(f"videos kept {len(v)} errors {bn.errors}")
for x in v: out.append(f"{x['date'][:10]} {x['game']:11} {x['kind']:7} | {x['title'][:100]} | {x['src']}")
# what the channels post that was skipped
import re
for cid, src, game in bn.YOUTUBE:
    xml = bn.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", browser=True)
    out.append(f"--- {src}: channel title {bn.text(bn.tag(xml, 'title'))}")
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S)[:15]:
        t = bn.text(bn.tag(e, "title")); g = game or bn.bandai_game(t)
        out.append(f"   {'KEEP' if g and not bn.VIDEO_SKIP_RE.search(t) else 'skip'} {bn.tag(e,'published')[:10]} {t[:100]}")
open("probe-report.txt", "w").write("\n".join(out))

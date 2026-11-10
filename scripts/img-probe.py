import subprocess
def head(url):
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-w", "SIZE %{size_download} CODE %{http_code}\n", "-H", "Origin: https://bilbosagggins.github.io", url], capture_output=True, text=True).stdout
    keep = [l.strip() for l in out.splitlines() if l.lower().startswith(("access-control-allow-origin", "content-type", "size"))]
    return " | ".join(keep)
for pid in ["517048", "197726", "718681"]:
    print("== product", pid)
    for suf in ["_200w.jpg", "_400w.jpg", "_600w.jpg", "_800w.jpg", "_in_200x200.jpg", "_in_400x400.jpg", "_in_500x500.jpg", "_in_600x600.jpg", "_in_800x800.jpg", "_in_1000x1000.jpg"]:
        print(f"  cdn {suf:18s}", head(f"https://tcgplayer-cdn.tcgplayer.com/product/{pid}{suf}"))
    for fit in ["fit-in/200x279", "fit-in/437x610", "fit-in/600x838", "fit-in/874x1220"]:
        print(f"  product-images {fit:16s}", head(f"https://product-images.tcgplayer.com/{fit}/{pid}.jpg"))

import subprocess
for ep in ["allSetCards/", "allSTCards/", "allPromoCards/", "allDonCards/", "allSets/"]:
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-w", "TIME %{time_total}s SIZE %{size_download}\n", "-H", "Origin: https://bilbosagggins.github.io",
                          "https://optcgapi.com/api/" + ep], capture_output=True, text=True).stdout
    keep = [l for l in out.splitlines() if l.lower().startswith(("http/", "access-control", "content-type", "location", "time", "cache-control", "content-encoding"))]
    print("==", ep); print("\n".join(keep))

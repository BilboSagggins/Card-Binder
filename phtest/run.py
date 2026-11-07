"""Real test of 📷 Photo page: the app in Chromium, the real CLIP model from transformers.js, Kyle's collection (read-only)."""
import asyncio, json, subprocess, sys, time, urllib.request
from playwright.async_api import async_playwright
API = "AIzaSyDOtaK7XgGBd6Yq5nBh7Ue9yJ41DlWQRrs"; DB = "https://card-binder-9879a-default-rtdb.firebaseio.com/"
def req(url, data=None):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={"User-Agent": "card-binder photo test", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())
tok = req(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API}", {"returnSecureToken": True})["idToken"]
coll = req(DB + "collections/kyle/pokemon.json?auth=" + tok)
FAKE = open("phtest/fake_fb.js").read()
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8811", "-d", "phtest"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 390, "height": 844}); errs = []; logs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: logs.append(m.text) if m.type in ("error", "warning") else None)
        async def route(r):
            u = r.request.url
            if "firebase-app-compat" in u: await r.fulfill(body=FAKE, content_type="text/javascript")
            elif "firebase-database-compat" in u or "firebase-auth-compat" in u: await r.fulfill(body="", content_type="text/javascript")
            else: await r.continue_()
        await pg.route("**/*", route)
        await pg.goto("http://localhost:8811/index.html"); await pg.wait_for_timeout(3000)
        await pg.evaluate("localStorage.setItem('cardBinder.unlocked', JSON.stringify(['kyle']))")
        await pg.evaluate("c => { firebase.database().ref('binders/kyle').set({ layout: '4x3', pages: [{ title: 'Mine', cards: Array(12).fill(null) }] }); firebase.database().ref('collections/kyle/pokemon').set(c); }", coll)
        await pg.evaluate("$('lb-scene').dataset.shape=''; renderShelf()"); await pg.wait_for_timeout(500)
        await pg.evaluate("document.querySelector('.lb-scene .bk[data-user=\"kyle\"]').click()"); await pg.wait_for_timeout(5000)
        TRUTH = {2: "197726", 3: "197728", 4: "189659", 9: "623588", 10: "517048", 12: "111643"}; EMPTY = {6, 7, 8}
        for dtype, inset in [("q8", .02), ("q8", .06), ("fp32", .02), ("fp32", .06)]:
            await pg.evaluate(f"() => {{ window.__phDtype = '{dtype}'; window.__phInset = {inset}; }}")
            if dtype == "fp32" and inset == .02: await pg.evaluate("() => { phModel = null; phLibP = null; }")
            await pg.evaluate("openPhotoPage()")
            await pg.set_input_files("#ph-pick label.alt input", "phtest/real-page.jpg"); await pg.wait_for_timeout(1500)
            await pg.evaluate("() => { const k = PH.img.width / 1482; PH.quad = [[22, 28], [1460, 28], [1460, 1543], [22, 1543]].map(([x, y]) => [x * k, y * k]); phDrawAlign(); }")
            t0 = time.time(); await pg.click("#ph-next")
            while time.time() - t0 < 1500:
                await pg.wait_for_timeout(4000)
                if not await pg.evaluate("$('ph-review').hidden") or not await pg.evaluate("$('ph-align').hidden"): break
            picks = await pg.evaluate("PH.pick.map(p => p.empty ? null : [String(p.card.tcgPid), p.card.name, p.sure, +(p.score||0).toFixed(3)])")
            right = sum(1 for i, pid in TRUTH.items() if picks[i - 1] and picks[i - 1][0] == pid)
            sure_right = sum(1 for i, pid in TRUTH.items() if picks[i - 1] and picks[i - 1][0] == pid and picks[i - 1][2])
            emp = sum(1 for i in range(1, 13) if (picks[i - 1] is None) == (i in EMPTY))
            print(f"== {dtype} inset {inset}: {round(time.time() - t0)}s | cards right {right}/6 (sure {sure_right}) | empty right {emp}/12", flush=True)
            for i, x in enumerate(picks, 1): print(f"   {i:2d}: " + ("EMPTY" if x is None else f"{x[1][:34]} [{x[0]}] {'sure' if x[2] else 'CHECK'} {x[3]}") + ("  <- want " + TRUTH[i] if i in TRUTH else ""))
            if inset == .02: await pg.screenshot(path=f"phtest/review-{dtype}.png", full_page=True)
            await pg.evaluate("closePhotoPage()")
        print("errors:", errs[:5]); print("console:", [l[:200] for l in logs if 'tailwind' not in l][:8])
        await b.close()
asyncio.run(main()); srv.terminate()

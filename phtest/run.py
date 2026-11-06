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
        await pg.evaluate("openPhotoPage()")
        await pg.set_input_files("#ph-pick label.alt input", "phtest/page.jpg"); await pg.wait_for_timeout(1500)
        await pg.evaluate("() => { const w = PH.img.width, h = PH.img.height; PH.quad = [[40, 40], [w - 40, 40], [w - 40, h - 40], [40, h - 40]]; phDrawAlign(); }")
        t0 = time.time(); await pg.click("#ph-next")
        last = ""
        while time.time() - t0 < 1500:
            await pg.wait_for_timeout(5000)
            t = await pg.evaluate("$('ph-work-t').textContent")
            if t != last: print(f"{time.time() - t0:5.0f}s {t}", flush=True); last = t
            if not await pg.evaluate("$('ph-review').hidden") or not await pg.evaluate("$('ph-align').hidden"): break
        print("done after", round(time.time() - t0), "s | review shown:", not await pg.evaluate("$('ph-review').hidden"))
        print("summary:", await pg.evaluate("$('ph-review-t') && $('ph-review-t').innerText"))
        picks = await pg.evaluate("PH.pick.map((p,i)=>(i+1)+': '+(p.empty?'EMPTY':p.card.name+' '+p.card.number+' ['+p.card.tcgPid+'] '+(p.sure?'sure':'CHECK')+' '+(p.score||0).toFixed(3)))")
        print("\n".join(picks))
        await pg.screenshot(path="phtest/review.png", full_page=True)
        # search fallback with the real model: pocket 11 (Team Rocket's Moltres ex, not in the collection)
        await pg.evaluate("phOpenCell(10)"); await pg.fill("#ph-q", "Team Rocket's Moltres"); await pg.click("#ph-go")
        for _ in range(60):
            await pg.wait_for_timeout(2000)
            if await pg.evaluate("document.querySelectorAll('#ph-found .ph-alt').length"): break
        print("search 'Team Rocket's Moltres' for pocket 11:", await pg.evaluate("[...document.querySelectorAll('#ph-found .ph-alt')].slice(0,4).map(b=>b.innerText.replace(/\\n/g,' | '))"))
        print("errors:", errs[:5]); print("console:", [l[:200] for l in logs if 'tailwind' not in l][:8])
        await b.close()
asyncio.run(main()); srv.terminate()

import asyncio, time, subprocess, os
from PIL import Image
from playwright.async_api import async_playwright
# a fake camera "filming" the sample page held inside the frame (portrait 1440 x 1920, like a phone)
VW, VH = 1440, 1920
a = (4 * 63 + 5 * 4) / (3 * 88 + 4 * 4); w = VW * 0.9; h = w / a
if h > VH * 0.9: h = VH * 0.9; w = h * a
x0, y0 = (VW - w) / 2, (VH - h) / 2
src = Image.open('site/photo-sample.jpg').convert('RGB'); sw, sh = src.size
quad = [(0.0199 * sw, 0.1198 * sh), (0.930 * sw, 0.1198 * sh), (0.930 * sw, 0.798 * sh), (0.012 * sw, 0.8025 * sh)]
bx0, by0 = min(q[0] for q in quad), min(q[1] for q in quad); bx1, by1 = max(q[0] for q in quad), max(q[1] for q in quad)
frame = src.resize((VW, VH)).point(lambda v: v // 3)
page = src.crop((int(bx0), int(by0), int(bx1), int(by1))).resize((int(w), int(h)))
frame.paste(page, (int(x0), int(y0)))
frame.save('live-frame.jpg', quality=85)
Y = frame.convert('YCbCr'); yy, cb, cr = Y.split()
cb = cb.resize((VW // 2, VH // 2)); cr = cr.resize((VW // 2, VH // 2))
with open('/tmp/page.y4m', 'wb') as f:
    f.write(f'YUV4MPEG2 W{VW} H{VH} F10:1 Ip A1:1 C420jpeg\n'.encode())
    for _ in range(4): f.write(b'FRAME\n' + yy.tobytes() + cb.tobytes() + cr.tobytes())
srv = subprocess.Popen(['python3', '-m', 'http.server', '8123', '--directory', 'site'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.5)
NOWRITE = """(() => { const t = setInterval(() => { try { const R = firebase.database.Reference.prototype; if (!R) return; clearInterval(t);
  for (const k of ['set', 'update', 'remove', 'push', 'transaction', 'setWithPriority']) R[k] = function () { console.log('BLOCKED WRITE ' + k); return Promise.resolve(); }; } catch (e) {} }, 5); })();"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-video-capture=/tmp/page.y4m'])
        ctx = await b.new_context(**p.devices['Pixel 7']); await ctx.grant_permissions(['camera'], origin='http://localhost:8123')
        pg = await ctx.new_page(); logs = []; pg.on('console', lambda m: logs.append(m.text))
        await pg.add_init_script(NOWRITE); await pg.add_init_script("localStorage.setItem('cardBinder.unlocked', JSON.stringify(['kyle']));")
        await pg.goto('http://localhost:8123/'); await pg.wait_for_function("!document.getElementById('landing').classList.contains('booting')", timeout=60000)
        await pg.evaluate("document.querySelector('.lb-scene .bk[data-user=\"kyle\"]').click()"); await pg.wait_for_function("typeof S !== 'undefined' && S.loadedFor", timeout=60000)
        print('binder layout', await pg.evaluate("S.layout"))
        await pg.evaluate("openPhotoPage()"); await pg.wait_for_timeout(500)
        t0 = time.time(); await pg.evaluate("phLiveStart()")
        await pg.wait_for_timeout(700); await pg.screenshot(path='site-live.png')
        await pg.wait_for_function("document.getElementById('ph-live').hidden", timeout=30000)
        print(f'captured by itself after {time.time() - t0:.1f}s; camera off: {await pg.evaluate("!LIVE.stream")}')
        await pg.wait_for_function("!document.getElementById('ph-review').hidden || !document.getElementById('ph-align').hidden", timeout=900000)
        print(f'results after {time.time() - t0:.1f}s from opening the camera')
        print('review:', await pg.evaluate("document.getElementById('ph-review-t').innerText"))
        print('pockets:', await pg.evaluate("PH.pick.map((p, i) => (i + 1) + ': ' + (p.empty ? 'empty' : p.card.name + ' [' + p.card.set + ' ' + p.card.number + '] ' + Math.round(p.score * 100) + '% ' + (p.sure ? 'sure' : 'check') + (p.collId ? ' (yours)' : ' (NEW)'))).join('\\n')"))
        await pg.screenshot(path='site-review.png')
        print('errors:', [l for l in logs if 'rror' in l][:6])
        await b.close()
asyncio.run(main()); srv.terminate()

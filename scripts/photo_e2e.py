import asyncio, time, subprocess, os, json
from playwright.async_api import async_playwright
srv = subprocess.Popen(['python3', '-m', 'http.server', '8123', '--directory', 'site'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
URL = 'http://localhost:8123/'
NOWRITE = """(() => { const t = setInterval(() => { try { const R = firebase.database.Reference.prototype; if (!R) return; clearInterval(t);
  for (const k of ['set', 'update', 'remove', 'push', 'transaction', 'setWithPriority']) R[k] = function () { console.log('BLOCKED WRITE ' + k + ' ' + this.toString().slice(0, 90)); return Promise.resolve(); }; } catch (e) {} }, 5); })();"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(**p.devices['Pixel 7'])
        pg = await ctx.new_page(); logs = []
        pg.on('console', lambda m: logs.append(m.text))
        cdp = await ctx.new_cdp_session(pg); await cdp.send('Network.enable'); reqs = {}
        cdp.on('Network.requestWillBeSent', lambda e: reqs.__setitem__(e['requestId'], {'url': e['request']['url']}))
        cdp.on('Network.loadingFinished', lambda e: reqs.get(e['requestId'], {}).update({'bytes': e['encodedDataLength']}))
        cdp.on('Network.responseReceived', lambda e: reqs.get(e['requestId'], {}).update({'sw': e['response'].get('fromServiceWorker'), 'disk': e['response'].get('fromDiskCache')}))
        await pg.add_init_script(NOWRITE)
        await pg.add_init_script("localStorage.setItem('cardBinder.unlocked', JSON.stringify(['kyle']));")
        await pg.goto(URL); await pg.wait_for_function("!document.getElementById('landing').classList.contains('booting')", timeout=60000)
        await pg.wait_for_timeout(2000)
        print('signed in anonymously:', await pg.evaluate("!!(firebase.auth && firebase.auth().currentUser && firebase.auth().currentUser.isAnonymous)"))
        print('helper URLs:', [r['url'][:90] for r in reqs.values() if 'auth/iframe' in r['url'] or 'apis.google.com' in r['url'] or 'firebaseapp.com' in r['url']])
        print('shelf binders:', await pg.evaluate("[...document.querySelectorAll('.lb-scene .bk')].map(b => b.dataset.user).slice(0, 8)"))
        # price lists: first visit, then again after a reload (should come from the phone)
        def net(since):
            rs = list(reqs.values())[since:]
            return sum(r.get('bytes', 0) for r in rs if 'raw.githubusercontent' in r['url'] and not r.get('sw')), len([r for r in rs if 'raw.githubusercontent' in r['url']])
        await pg.evaluate("document.querySelector('.lb-scene .bk[data-user=\"kyle\"]').click()")
        await pg.wait_for_function("typeof S !== 'undefined' && S.loadedFor", timeout=60000)
        print('binder game:', await pg.evaluate("S.game"), '| collection items:', await pg.evaluate("Object.keys((COLLECTIONS[collKey()] || {}).items || {}).length"))
        n = len(reqs); a = time.time(); await pg.evaluate("openPricePage()"); await pg.wait_for_function("PC.ready", timeout=90000)
        await pg.wait_for_timeout(1500); bts, cnt = net(n); print(f'Prices 1st time: {time.time()-a:.1f}s, {cnt} data requests, {bts/1048576:.2f} MB')
        saved = "(async () => { const c = await caches.open('cb-data-v1'); const out = {}; for (const k of await c.keys()) { const r = await c.match(k); out[k.url.split('/').slice(-2).join('/')] = r.headers.get('x-cb-saved'); } return out; })()"
        before = await pg.evaluate(saved); print('saved copies before reload:', before)
        await pg.reload(); await pg.wait_for_function("!document.getElementById('landing').classList.contains('booting')", timeout=60000); await pg.wait_for_timeout(1500)
        print('page controlled by offline helper:', await pg.evaluate("!!navigator.serviceWorker.controller"))
        await pg.evaluate("document.querySelector('.lb-scene .bk[data-user=\"kyle\"]').click()"); await pg.wait_for_function("typeof S !== 'undefined' && S.loadedFor", timeout=60000)
        n = len(reqs); a = time.time(); await pg.evaluate("openPricePage()"); await pg.wait_for_function("PC.ready", timeout=90000)
        await pg.wait_for_timeout(1500)
        rs = list(reqs.values())[n:]; data = [r for r in rs if 'raw.githubusercontent' in r['url']]
        print(f'Prices after reload: {time.time()-a:.1f}s, {len(data)} data requests, from offline helper: {sum(1 for r in data if r.get("sw"))}, internet bytes: {sum(r.get("bytes",0) for r in data if not r.get("sw"))/1048576:.2f} MB')
        after = await pg.evaluate(saved); print('re-downloaded after reload:', [k for k in after if before.get(k) != after.get(k)] or 'none')
        await pg.evaluate("closePricePage()")
        return await b.close()
        # photo page with the sample
        a = time.time(); await pg.evaluate("openPhotoPage()"); await pg.wait_for_timeout(500)
        await pg.evaluate("phTrySample()"); await pg.wait_for_function("PH.img && !document.getElementById('ph-align').hidden", timeout=30000)
        await pg.screenshot(path='site-align.png')
        print('waiting while "lining up corners" (prep runs in the background)'); await pg.wait_for_timeout(5000)
        b0 = time.time(); await pg.evaluate("phMatch()")
        await pg.wait_for_function("!document.getElementById('ph-review').hidden || !document.getElementById('ph-align').hidden", timeout=900000)
        print(f'match took {time.time()-b0:.1f}s after tapping (page opened {time.time()-a:.1f}s ago)')
        print('timing:', await pg.evaluate("JSON.stringify(PH.timing)"))
        print('review:', await pg.evaluate("document.getElementById('ph-review-t').innerText"))
        print('pockets:', await pg.evaluate("PH.pick.map((p, i) => (i + 1) + ': ' + (p.empty ? 'empty' : p.card.name + ' [' + p.card.set + ' ' + p.card.number + '] ' + Math.round(p.score * 100) + '% ' + (p.sure ? 'sure' : 'check'))).join('\\n')"))
        await pg.screenshot(path='site-review.png', full_page=False)
        print('blocked writes:', [l for l in logs if 'BLOCKED' in l][:5]); print('errors:', [l for l in logs if 'rror' in l][:6])
        await b.close()
asyncio.run(main()); srv.terminate()

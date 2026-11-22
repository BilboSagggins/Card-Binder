import asyncio, json, time, collections
from playwright.async_api import async_playwright
URL = 'https://bilbosagggins.github.io/Card-Binder/'
NOWRITE = """
(() => { const t = setInterval(() => { try { const R = firebase.database.Reference.prototype; if (!R) return; clearInterval(t);
  for (const k of ['set', 'update', 'remove', 'push', 'transaction', 'setWithPriority']) R[k] = function () { console.log('BLOCKED WRITE ' + k + ' ' + this.toString().slice(0, 90)); return Promise.resolve(); };
} catch (e) {} }, 5); })();
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(**p.devices['Pixel 7'])
        pg = await ctx.new_page()
        cdp = await ctx.new_cdp_session(pg)
        await cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        await cdp.send('Network.enable')
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 60, 'downloadThroughput': 12 * 1024 * 1024 / 8, 'uploadThroughput': 3 * 1024 * 1024 / 8})
        reqs = {}; logs = []
        cdp.on('Network.requestWillBeSent', lambda e: reqs.__setitem__(e['requestId'], {'url': e['request']['url'], 't0': e['timestamp']}))
        cdp.on('Network.loadingFinished', lambda e: reqs.get(e['requestId'], {}).update({'bytes': e['encodedDataLength'], 't1': e['timestamp']}))
        pg.on('console', lambda m: logs.append(m.text))
        await pg.add_init_script(NOWRITE)
        await pg.add_init_script("localStorage.setItem('cardBinder.unlocked', JSON.stringify(['kyle']));")
        T = time.time(); marks = {}
        await pg.goto(URL, wait_until='domcontentloaded'); marks['domcontentloaded'] = time.time() - T
        await pg.wait_for_function("!document.getElementById('landing').classList.contains('booting')", timeout=60000); marks['shelf visible'] = time.time() - T
        await pg.wait_for_timeout(1500)
        def snap(label):
            tot = sum(r.get('bytes', 0) for r in reqs.values()); print(f'--- {label}: {len(reqs)} requests, {tot/1048576:.2f} MB')
        snap('after shelf')
        by = collections.Counter(); size = collections.Counter()
        for r in reqs.values():
            u = r['url'].split('?')[0]; by[u] += 1; size[u] += r.get('bytes', 0)
        for u, s in size.most_common(14): print(f'   {s/1024:8.0f} KB  x{by[u]}  {u[:110]}')
        # open the first binder on the shelf
        T2 = time.time()
        await pg.evaluate("document.querySelector('.lb-scene .bk[data-user=\"kyle\"]') ? document.querySelector('.lb-scene .bk[data-user=\"kyle\"]').click() : document.querySelector('.lb-scene .bk').click()")
        await pg.wait_for_function("document.querySelectorAll('#grid .slot').length > 0 && typeof S !== 'undefined' && S.loadedFor", timeout=60000); marks['binder shown'] = time.time() - T2
        await pg.wait_for_timeout(4000)
        n0 = len(reqs); snap('after binder')
        info = await pg.evaluate("({ pages: getPagesArray().length, cards: getPagesArray().flatMap(p => p.cards).filter(Boolean).length, layout: S.layout, heap: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null, imgs: document.images.length })")
        print('binder', info)
        # render cost
        t = await pg.evaluate("(() => { const a = performance.now(); for (let i = 0; i < 5; i++) render(); return (performance.now() - a) / 5; })()"); print(f'render(): {t:.0f} ms each')
        t = await pg.evaluate("(() => { const a = performance.now(); go(1); go(-1); return (performance.now() - a) / 2; })()"); print(f'page turn: {t:.0f} ms')
        for name, js, done in [('Need list', 'openNeedPage()', "document.querySelectorAll('#np-grid .np-card').length > 0 || document.querySelector('#np-grid .np-empty')"),
                               ('Collection', "tabGo('coll')", "document.querySelectorAll('#coll-results > *').length > 0 || true"),
                               ('Prices', 'openPricePage()', "typeof PC !== 'undefined' && PC.ready"),
                               ('News', 'openNewsPage()', "document.querySelectorAll('#nw-list .nw-card').length > 0")]:
            a = time.time(); r0 = len(reqs)
            try:
                await pg.evaluate(js); await pg.wait_for_function(done, timeout=60000)
                print(f'{name}: {time.time() - a:.1f} s, {len(reqs) - r0} requests, {sum(r.get("bytes", 0) for r in list(reqs.values())[r0:])/1048576:.2f} MB')
            except Exception as e: print(name, 'ERR', str(e)[:120])
            await pg.evaluate("closeAllPages && closeAllPages()") if name != 'Collection' else None
            await pg.wait_for_timeout(800)
        print('marks', {k: round(v, 1) for k, v in marks.items()})
        lt = await pg.evaluate("(() => { const e = performance.getEntriesByType('longtask'); return e.length })()")
        print('blocked writes:', [l for l in logs if 'BLOCKED' in l][:8])
        print('console errors:', [l for l in logs if 'rror' in l][:6])
        await b.close()
asyncio.run(main())

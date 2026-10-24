/* Card Binder offline helper (service worker).
   Keeps the app, its scripts and fonts, the daily price lists, the news, and card pictures on the phone,
   so the binder opens and works with no signal (for example at a card show).
   - The app page and the price lists: fresh from the internet when there is signal, the saved copy when not.
   - Scripts, fonts and card pictures: the saved copy first (they never change), fetched and saved when missing.
   - Firebase (your binder data and sign-in) is never touched here; the app keeps its own copy of your binders. */
const SHELL = 'cb-shell-v1', DATA = 'cb-data-v1', IMG = 'cb-img-v1';
const IMG_MAX = 4000, OPAQUE_MAX = 600;     // pictures kept; pictures from sites that don't allow sharing count more against storage
const SHELL_FILES = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png'];
const LIBS = [
  'https://cdn.tailwindcss.com',
  'https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js',
  'https://www.gstatic.com/firebasejs/9.23.0/firebase-database-compat.js',
  'https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js',
];
const IMG_HOSTS = /(^|\.)(tcgplayer-cdn\.tcgplayer\.com|product-images\.tcgplayer\.com|assets\.tcgdex\.net|images\.pokemontcg\.io|i\.ytimg\.com|onepiece-cardgame\.com|pokebeach\.com|cardtrader\.com|cmsassets\.rgpub\.io|static\.animecorner\.me)$/;
const OPAQUE_OK = /(^|\.)(product-images\.tcgplayer\.com|onepiece-cardgame\.com|cdn\.tailwindcss\.com)$/;   // no sharing headers, but worth keeping
const LIB_HOSTS = /(^|\.)(cdn\.tailwindcss\.com|gstatic\.com|fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|unpkg\.com)$/;
const DATA_HOSTS = /(^|\.)raw\.githubusercontent\.com$/;
const SKIP_HOSTS = /firebaseio\.com|firebasedatabase\.app|googleapis\.com\/identitytoolkit|securetoken|identitytoolkit|firebaseinstallations|google-analytics|googletagmanager/;

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const shell = await caches.open(SHELL);
    await Promise.all(SHELL_FILES.map(u => shell.add(new Request(u, { cache: 'reload' })).catch(() => {})));
    await Promise.all(LIBS.map(async u => { try { const r = await fetch(u, { mode: 'no-cors' }); await shell.put(u, r); } catch (err) {} }));
    self.skipWaiting();
  })());
});
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keep = [SHELL, DATA, IMG];
    for (const k of await caches.keys()) if (!keep.includes(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

const timeout = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms))]);
// The page itself (and ?v= / ?check= copies of it) is saved under one plain address
const pageKey = url => { const u = new URL(url); u.search = ''; u.hash = ''; if (u.pathname.endsWith('/')) u.pathname += 'index.html'; return u.href; };

async function networkFirst(req, cacheName, key, ms) {
  const cache = await caches.open(cacheName);
  try {
    const res = await timeout(fetch(req), ms);
    if (res && res.ok) cache.put(key, res.clone()).catch(() => {});
    return res;
  } catch (err) {
    const hit = await cache.match(key, { ignoreSearch: true }) || await caches.match(key, { ignoreSearch: true });
    if (hit) return hit;
    throw err;
  }
}
async function cacheFirst(req, cacheName, key) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(key || req, { ignoreSearch: false }) || await caches.match(key || req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res && (res.ok || res.type === 'opaque')) cache.put(key || req, res.clone()).catch(() => {});
  return res;
}
let trimming = false;
async function trimImages() {
  if (trimming) return; trimming = true;
  try {
    const cache = await caches.open(IMG), keys = await cache.keys();
    if (keys.length > IMG_MAX) for (const k of keys.slice(0, keys.length - IMG_MAX)) await cache.delete(k);
  } catch (err) {} finally { trimming = false; }
}
async function picture(req) {
  const url = req.url, cache = await caches.open(IMG);
  const hit = await cache.match(url, { ignoreVary: true });
  if (hit) return hit;
  // Ask with sharing headers first: those pictures are stored at their real size
  try {
    const res = await fetch(url, { mode: 'cors', credentials: 'omit', referrerPolicy: 'no-referrer' });
    if (res.ok) { cache.put(url, res.clone()).then(trimImages).catch(() => {}); return res; }
  } catch (err) {}
  const res = await fetch(req.mode === 'cors' ? new Request(url, { mode: 'no-cors', referrerPolicy: 'no-referrer' }) : req);
  if (res.type === 'opaque' && OPAQUE_OK.test(new URL(url).hostname)) {
    const n = (await cache.keys()).length;
    if (n < OPAQUE_MAX * 4) cache.put(url, res.clone()).catch(() => {});
  } else if (res.ok) cache.put(url, res.clone()).then(trimImages).catch(() => {});
  return res;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.protocol !== 'https:' && url.protocol !== 'http:') return;
  if (SKIP_HOSTS.test(url.hostname + url.pathname)) return;           // Firebase: live data and sign-in, never stored here
  const same = url.origin === self.location.origin;

  if (same && (req.mode === 'navigate' || /\/(index\.html)?$/.test(url.pathname))) {
    return e.respondWith(networkFirst(req, SHELL, pageKey(req.url), 4000));
  }
  if (same && /\/(prices|news)\/[^/]+\.json$/.test(url.pathname)) return e.respondWith(networkFirst(req, DATA, url.origin + url.pathname, 8000));
  if (same) return e.respondWith(cacheFirst(req, SHELL).catch(() => fetch(req)));
  if (DATA_HOSTS.test(url.hostname)) return e.respondWith(networkFirst(req, DATA, url.origin + url.pathname, 8000));
  if (LIB_HOSTS.test(url.hostname) && !IMG_HOSTS.test(url.hostname)) return e.respondWith(cacheFirst(req, SHELL, url.href).catch(() => fetch(req)));
  if (IMG_HOSTS.test(url.hostname) && (req.destination === 'image' || /\.(jpe?g|png|webp|gif|avif)(\?|$)/i.test(url.pathname))) {
    return e.respondWith(picture(req).catch(() => caches.match(req.url).then(r => r || Response.error())));
  }
  // anything else (card search database, outside pages): straight to the internet
});

// The app can ask how many pictures are saved
self.addEventListener('message', e => {
  if (e.data === 'count') caches.open(IMG).then(c => c.keys()).then(k => e.source && e.source.postMessage({ type: 'count', images: k.length })).catch(() => {});
});

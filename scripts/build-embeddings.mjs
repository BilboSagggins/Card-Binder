/* Picture fingerprints for the 📷 Photo page: every card in the daily price lists is looked at once here, by the same
   picture-matching AI the phone uses (CLIP ViT-B/16 through transformers.js), so the phone no longer has to download and look at
   every card in your collection itself. The same full-size picture, shrunk to 448 px like the phone does, gives the same
   fingerprint as the phone's (checked: 1.0000; TCGplayer's 400 px pictures are framed differently and only reach 0.95). Same two looks as the phone: the whole card, and its top 60%, added together.

   emb/<list>/<setId>.bin: one record per card, [product id: uint32][scale: float32][512 × int8] (vector = int8 × scale).
   Cards with no picture yet are left out and tried again next run. emb/index.json says which sets are done. Works through the lists within a time budget and picks up
   where it stopped next run, so the first full pass takes a few runs; after that only new cards are looked at. */
import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env } from '@huggingface/transformers';
import fs from 'fs';
import path from 'path';

env.allowLocalModels = false;
const MODEL = 'Xenova/clip-vit-base-patch16', DIMS = 512;
const LISTS = ['onepiece', 'pokemon', 'pokemon-zh', 'pokemon-jp'];   // One Piece first (small), then English, Chinese, Japanese
const BUDGET_MS = (+process.env.BUDGET_MIN || 300) * 60000, START = Date.now();
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const OUT = path.join(ROOT, 'emb');
fs.mkdirSync(OUT, { recursive: true });

const indexPath = path.join(OUT, 'index.json');
const index = fs.existsSync(indexPath) ? JSON.parse(fs.readFileSync(indexPath, 'utf8')) : { model: MODEL, dims: DIMS, lists: {} };

const proc = await AutoProcessor.from_pretrained(MODEL);
const vision = await CLIPVisionModelWithProjection.from_pretrained(MODEL, { dtype: 'fp32' });
console.log('model ready');

const norm = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) || 1; return Float32Array.from(v, x => x / s); };
// TCGplayer's picture, or CardTrader's for the Chinese list (its picture path is in the list)
const CT_IMG = 'https://www.cardtrader.com/uploads/blueprints/image/';
async function load(pid, L) {
  const e = L.p[pid], url = L.source === 'cardtrader' ? (e[5] ? CT_IMG + e[5] : null) : `https://tcgplayer-cdn.tcgplayer.com/product/${pid}_in_1000x1000.jpg`;
  if (!url) return null;
  for (let i = 0; i < 3; i++) {
    try {
      let img = await RawImage.read(url);
      const k = Math.min(1, 448 / Math.max(img.width, img.height));
      if (k < 1) img = await img.resize(Math.round(img.width * k), Math.round(img.height * k));
      return img;
    } catch (e) { if (/404|403/.test(String(e))) return null; await new Promise(r => setTimeout(r, 1500 * (i + 1))); }
  }
  return null;
}
// a batch of cards -> one fingerprint each (null when there's no picture)
async function embedBatch(imgs) {
  const views = [], owner = [];
  imgs.forEach((img, i) => { if (!img) return; views.push(img, img.crop([0, 0, img.width - 1, Math.round(img.height * 0.6) - 1])); owner.push(i, i); });
  const out = imgs.map(() => null);
  if (!views.length) return out;
  const crops = await Promise.all(views);
  const { image_embeds } = await vision(await proc(crops));
  const sums = imgs.map(() => null);
  for (let v = 0; v < crops.length; v++) {
    const e = norm(image_embeds.data.slice(v * DIMS, (v + 1) * DIMS)), i = owner[v];
    sums[i] = sums[i] ? sums[i].map((x, d) => x + e[d]) : e;
  }
  sums.forEach((s, i) => { if (s) out[i] = norm(s); });
  return out;
}
function pack(rows) {           // rows: [pid, Float32Array|null]
  const rec = 8 + DIMS, buf = Buffer.alloc(rows.length * rec);
  rows.forEach(([pid, v], r) => {
    const o = r * rec; buf.writeUInt32LE(+pid, o);
    if (!v) { buf.writeFloatLE(0, o + 4); return; }
    let m = 0; for (const x of v) m = Math.max(m, Math.abs(x)); const scale = m / 127 || 1e-9;
    buf.writeFloatLE(scale, o + 4);
    for (let d = 0; d < DIMS; d++) buf.writeInt8(Math.max(-127, Math.min(127, Math.round(v[d] / scale))), o + 8 + d);
  });
  return buf;
}
function unpack(buf) {
  const rec = 8 + DIMS, out = new Map();
  for (let o = 0; o + rec <= buf.length; o += rec) out.set(String(buf.readUInt32LE(o)), buf.subarray(o, o + rec));
  return out;
}

let done = 0, noPic = 0, outOfTime = false;
for (const list of LISTS) {
  const L = JSON.parse(fs.readFileSync(path.join(ROOT, 'prices', `${list}.json`), 'utf8'));
  const dir = path.join(OUT, list); fs.mkdirSync(dir, { recursive: true });
  const byGroup = {};
  for (const [pid, e] of Object.entries(L.p)) (byGroup[e[3]] ||= []).push(pid);
  index.lists[list] ||= {};
  for (const gid of Object.keys(byGroup).sort((a, b) => +b - +a)) {      // newest sets first
    const file = path.join(dir, `${gid}.bin`);
    const have = fs.existsSync(file) ? unpack(fs.readFileSync(file)) : new Map();
    const todo = byGroup[gid].filter(p => !have.has(p));
    if (!todo.length) { index.lists[list][gid] = have.size; continue; }
    if (Date.now() - START > BUDGET_MS) { outOfTime = true; break; }
    const fresh = [];
    const get = p => load(p, L);
    let next = Promise.all(todo.slice(0, 8).map(get));
    for (let i = 0; i < todo.length; i += 8) {
      const imgs = await next;
      next = Promise.all(todo.slice(i + 8, i + 16).map(get));          // fetch the next pictures while the AI works
      const vecs = await embedBatch(imgs);
      todo.slice(i, i + 8).forEach((p, j) => { if (vecs[j]) fresh.push([p, vecs[j]]); else noPic++; });   // no picture yet: tried again next run
    }
    if (!fresh.length) continue;
    fs.writeFileSync(file, Buffer.concat([...have.values(), pack(fresh)]));
    index.lists[list][gid] = have.size + fresh.length; done += fresh.length;
    fs.writeFileSync(indexPath, JSON.stringify({ ...index, updated: new Date().toISOString() }));
    console.log(`${list} ${L.groups[gid] || gid}: +${fresh.length} (${((Date.now() - START) / 60000).toFixed(1)} min, ${done} this run)`);
  }
  if (outOfTime) break;
}
index.complete = !outOfTime;
fs.writeFileSync(indexPath, JSON.stringify({ ...index, updated: new Date().toISOString() }));
console.log((outOfTime ? `Out of time after ${done} cards; the next run carries on.` : `All sets done (${done} new cards this run).`) + (noPic ? ` ${noPic} cards have no picture yet.` : ''));

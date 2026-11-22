import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env } from '@huggingface/transformers';
import fs from 'fs';
env.allowLocalModels = false;
const M = 'Xenova/clip-vit-base-patch16';
const proc = await AutoProcessor.from_pretrained(M);
const server = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: 'fp32' });
const phone = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: 'fp16' });
const norm = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) || 1; return Float32Array.from(v, x => x / s); };
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
async function two(model, img) {
  const top = await img.crop([0, 0, img.width - 1, Math.round(img.height * .6) - 1]);
  const o = await model(await proc([img, top])), d = 512, a = norm(o.image_embeds.data.slice(0, d)), b = norm(o.image_embeds.data.slice(d, 2 * d));
  return { full: a, card: norm(a.map((x, i) => x + b[i])) };
}
const fit = async (img, max) => { const k = Math.min(1, max / Math.max(img.width, img.height)); return k < 1 ? img.resize(Math.round(img.width * k), Math.round(img.height * k)) : img; };
// candidate pool, made like the job: TCGplayer 400px picture, full precision
const pool = [];
for (const list of ['pokemon', 'pokemon-jp']) {
  const L = JSON.parse(fs.readFileSync(`prices/${list}.json`));
  for (const [pid, e] of Object.entries(L.p)) if (/moltres|zapdos|articuno|lugia|ho-oh/i.test(e[1])) pool.push({ pid, list, name: e[1], set: L.groups[e[3]], num: e[2] });
}
console.log('pool', pool.length);
let t = Date.now();
for (let i = 0; i < pool.length; i += 8) {
  const imgs = await Promise.all(pool.slice(i, i + 8).map(async c => { try { return await fit(await RawImage.read(`https://tcgplayer-cdn.tcgplayer.com/product/${c.pid}_in_400x400.jpg`), 448); } catch (e) { return null; } }));
  for (const [j, img] of imgs.entries()) if (img) pool[i + j].emb = (await two(server, img)).card;
}
console.log('pool done in', ((Date.now() - t) / 1000).toFixed(0), 's;', pool.filter(c => c.emb).length, 'with pictures');
// server vs phone fingerprint for the same few cards (phone: the 1000px picture shrunk to 448, half precision)
for (const c of pool.filter(c => c.emb).slice(0, 5)) {
  const img = await fit(await RawImage.read(`https://tcgplayer-cdn.tcgplayer.com/product/${c.pid}_in_1000x1000.jpg`), 448);
  console.log('server vs phone', c.name, dot(c.emb, (await two(phone, img)).card).toFixed(4));
}
// pockets, cut like the phone does
let page = await RawImage.read('data/page.jpg'); page = await fit(page, 2200);
const W = page.width / 1659;
const Q = [[33, 265], [1543, 265], [1543, 1765], [20, 1775]].map(([x, y]) => [x * W, y * W]);
const at = (u, v) => { const [a, b, c, d] = Q; return [a[0]*(1-u)*(1-v)+b[0]*u*(1-v)+c[0]*u*v+d[0]*(1-u)*v, a[1]*(1-u)*(1-v)+b[1]*u*(1-v)+c[1]*u*v+d[1]*(1-u)*v]; };
const usable = pool.filter(c => c.emb);
for (let r = 0; r < 3; r++) for (let col = 0; col < 4; col++) {
  const pts = [[col, r], [col + 1, r], [col + 1, r + 1], [col, r + 1]].map(([u, v]) => at(u / 4, v / 3));
  let x0 = Math.min(...pts.map(p => p[0])), x1 = Math.max(...pts.map(p => p[0])), y0 = Math.min(...pts.map(p => p[1])), y1 = Math.max(...pts.map(p => p[1]));
  const ix = (x1 - x0) * .02, iy = (y1 - y0) * .02; x0 += ix; x1 -= ix; y0 += iy; y1 -= iy;
  const cell = await fit(await page.crop([Math.round(x0), Math.round(y0), Math.round(x1), Math.round(y1)]), 448);
  const e = (await two(phone, cell)).card;
  const top = usable.map(c => [c, dot(e, c.emb)]).sort((a, b) => b[1] - a[1]).slice(0, 3);
  console.log(`pocket ${r * 4 + col + 1}:`, top.map(([c, s]) => `${c.name} [${c.set} ${c.num}] ${s.toFixed(3)}`).join(' | '));
}

import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env } from '@huggingface/transformers';
import fs from 'fs'; import path from 'path';
env.allowLocalModels = false;
const M = 'Xenova/clip-vit-base-patch16';
const proc = await AutoProcessor.from_pretrained(M);
const phone = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: 'fp16' });
const norm = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) || 1; return Float32Array.from(v, x => x / s); };
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
const fit = async (img, max) => { const k = Math.min(1, max / Math.max(img.width, img.height)); return k < 1 ? img.resize(Math.round(img.width * k), Math.round(img.height * k)) : img; };
async function two(img) { const top = await img.crop([0, 0, img.width - 1, Math.round(img.height * .6) - 1]); const o = await phone(await proc([img, top])), a = norm(o.image_embeds.data.slice(0, 512)), b = norm(o.image_embeds.data.slice(512, 1024)); return norm(a.map((x, i) => x + b[i])); }
// all fingerprints
const cards = []; const names = {};
for (const list of ['onepiece', 'pokemon', 'pokemon-zh', 'pokemon-jp']) {
  const L = JSON.parse(fs.readFileSync(`prices/${list}.json`)); names[list] = L;
  for (const f of fs.readdirSync(`emb/${list}`)) { const b = fs.readFileSync(`emb/${list}/${f}`); for (let o = 0; o + 520 <= b.length; o += 520) { const id = String(b.readUInt32LE(o)), sc = b.readFloatLE(o + 4); if (!sc) continue; const v = new Float32Array(512); for (let d = 0; d < 512; d++) v[d] = b.readInt8(o + 8 + d) * sc; cards.push({ list, id, v: norm(v) }); } }
}
console.log('cards', cards.length);
const pk = cards.filter(c => c.list !== 'onepiece');
const mean = l => { const m = new Float32Array(512); const s = pk.filter(c => !l || c.list === l); for (const c of s) for (let d = 0; d < 512; d++) m[d] += c.v[d] / s.length; return m; };
const gm = mean(), lm = { pokemon: mean('pokemon'), 'pokemon-zh': mean('pokemon-zh'), 'pokemon-jp': mean('pokemon-jp') };
console.log('list means: |zh-en|', Math.sqrt(dot(lm['pokemon-zh'].map((x, d) => x - lm.pokemon[d]), lm['pokemon-zh'].map((x, d) => x - lm.pokemon[d]))).toFixed(3), ' |jp-en|', Math.sqrt(dot(lm['pokemon-jp'].map((x, d) => x - lm.pokemon[d]), lm['pokemon-jp'].map((x, d) => x - lm.pokemon[d]))).toFixed(3));
// pockets
let page = await fit(await RawImage.read('site/photo-sample.jpg'), 2200);
const Q = [[0.0199, 0.1198], [0.930, 0.1198], [0.930, 0.798], [0.012, 0.8025]].map(([x, y]) => [x * page.width, y * page.height]);
const at = (u, v) => { const [a, b, c, d] = Q; return [a[0]*(1-u)*(1-v)+b[0]*u*(1-v)+c[0]*u*v+d[0]*(1-u)*v, a[1]*(1-u)*(1-v)+b[1]*u*(1-v)+c[1]*u*v+d[1]*(1-u)*v]; };
const want = { 1: /moltres & zapdos/i, 2: /moltres & zapdos/i, 3: /moltres & zapdos/i, 4: /moltres & zapdos/i, 5: /moltres & zapdos/i, 9: /articuno/i, 10: /zapdos/i, 11: /moltres/i, 12: /ho-oh/i };
const pockets = [];
for (let r = 0; r < 3; r++) for (let col = 0; col < 4; col++) {
  const i = r * 4 + col + 1; if (!want[i]) continue;
  const pts = [[col, r], [col + 1, r], [col + 1, r + 1], [col, r + 1]].map(([u, v]) => at(u / 4, v / 3));
  let x0 = Math.min(...pts.map(p => p[0])), x1 = Math.max(...pts.map(p => p[0])), y0 = Math.min(...pts.map(p => p[1])), y1 = Math.max(...pts.map(p => p[1]));
  const ix = (x1 - x0) * .02, iy = (y1 - y0) * .02;
  pockets.push({ i, e: await two(await fit(await page.crop([Math.round(x0 + ix), Math.round(y0 + iy), Math.round(x1 - ix), Math.round(y1 - iy)]), 448)) });
}
fs.writeFileSync('pockets.json', JSON.stringify(Object.fromEntries(pockets.map(p => [p.i, Array.from(p.e)]))));
process.exit(0);
const nm = c => names[c.list].p[c.id][1] + ' [' + (names[c.list].groups[names[c.list].p[c.id][3]] || '') + (c.list !== 'pokemon' ? ' ' + c.list.slice(8) : '') + ']';
const methods = {
  raw: (q, c) => dot(q, c.v),
  globalCentered: (q, c) => { const a = q.map((x, d) => x - gm[d]), b = c.v.map((x, d) => x - gm[d]); return dot(a, b) / Math.sqrt(dot(a, a) * dot(b, b)); },
  listCentered: (q, c) => { const m = lm[c.list]; const a = q.map((x, d) => x - gm[d]), b = c.v.map((x, d) => x - m[d]); return dot(a, b) / Math.sqrt(dot(a, a) * dot(b, b)); },
};
// precompute centered card vectors for speed
for (const [k, fn] of Object.entries(methods)) {
  let right = 0; const lines = [];
  for (const p of pockets) {
    const best = pk.map(c => [fn(p.e, c), c]).sort((a, b) => b[0] - a[0]).slice(0, 3);
    const ok = want[p.i].test(nm(best[0][1])); right += ok;
    lines.push(`  ${p.i}: ${ok ? 'OK ' : 'no '} ` + best.map(([s, c]) => nm(c) + ' ' + s.toFixed(3)).join(' | '));
  }
  console.log(`== ${k}: right Pokémon on top in ${right} of ${pockets.length}`); console.log(lines.join('\n'));
}

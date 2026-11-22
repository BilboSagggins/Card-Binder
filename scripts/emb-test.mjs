import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env } from '@huggingface/transformers';
import fs from 'fs';
env.allowLocalModels = false;
const M = 'Xenova/clip-vit-base-patch16';
const t0 = Date.now();
const proc = await AutoProcessor.from_pretrained(M);
const vision = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: process.env.DT || 'fp32' });
console.log('model ready', (Date.now() - t0) / 1000, 's');
const L = JSON.parse(fs.readFileSync('prices/pokemon.json'));
const gid = Object.entries(L.groups).find(([g, n]) => n === 'SV08: Surging Sparks')[0];
const pids = Object.entries(L.p).filter(([, e]) => String(e[3]) === gid).map(([p]) => p).slice(0, 40);
const norm = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) || 1; return Float32Array.from(v, x => x / s); };
async function emb(img) { const o = await vision(await proc(img)); return norm(o.image_embeds.data); }
let tdl = 0, tin = 0;
for (const size of ['200w', 'in_400x400']) {
  tdl = 0; tin = 0; const t1 = Date.now();
  for (const pid of pids.slice(0, 20)) {
    const a = Date.now(); let img = await RawImage.read(`https://tcgplayer-cdn.tcgplayer.com/product/${pid}_${size}.jpg`); tdl += Date.now() - a;
    const k = Math.min(1, 448 / Math.max(img.width, img.height)); if (k < 1) img = await img.resize(Math.round(img.width * k), Math.round(img.height * k));
    const b = Date.now(); const full = await emb(img); const top = await emb(await img.crop([0, 0, img.width - 1, Math.round(img.height * .6) - 1])); tin += Date.now() - b;
  }
  console.log(size, 'per card: download', (tdl / 20).toFixed(0), 'ms, AI', (tin / 20).toFixed(0), 'ms (2 views); total', ((Date.now() - t1) / 1000).toFixed(1), 's');
}

import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env } from '@huggingface/transformers';
env.allowLocalModels = false;
const M = 'Xenova/clip-vit-base-patch16';
const proc = await AutoProcessor.from_pretrained(M);
const f32 = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: 'fp32' });
const f16 = await CLIPVisionModelWithProjection.from_pretrained(M, { dtype: 'fp16' });
const norm = v => { let s = 0; for (const x of v) s += x * x; s = Math.sqrt(s) || 1; return Float32Array.from(v, x => x / s); };
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
async function two(model, img) { const top = await img.crop([0, 0, img.width - 1, Math.round(img.height * .6) - 1]); const o = await model(await proc([img, top])), a = norm(o.image_embeds.data.slice(0, 512)), b = norm(o.image_embeds.data.slice(512, 1024)); return norm(a.map((x, i) => x + b[i])); }
const fit = async (img, max) => { const k = Math.min(1, max / Math.max(img.width, img.height)); return k < 1 ? img.resize(Math.round(img.width * k), Math.round(img.height * k)) : img; };
const pids = ['610513', '90143', '42382', '527035', '557286', '454536'];
let s = { '32/400': 0, '16/400': 0, '32/1000': 0 }, n = 0;
for (const p of pids) {
  try {
    const big = await fit(await RawImage.read(`https://tcgplayer-cdn.tcgplayer.com/product/${p}_in_1000x1000.jpg`), 448), small = await fit(await RawImage.read(`https://tcgplayer-cdn.tcgplayer.com/product/${p}_in_400x400.jpg`), 448);
    const phone = await two(f16, big);
    const r = { '32/400': dot(phone, await two(f32, small)), '16/400': dot(phone, await two(f16, small)), '32/1000': dot(phone, await two(f32, big)) };
    console.log(p, Object.entries(r).map(([k, v]) => k + ' ' + v.toFixed(4)).join('  ')); for (const k in r) s[k] += r[k]; n++;
  } catch (e) { console.log(p, 'err', String(e).slice(0, 80)); }
}
console.log('average vs phone', Object.entries(s).map(([k, v]) => k + ' ' + (v / n).toFixed(4)).join('  '));

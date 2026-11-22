import fs from 'fs';
const idx = JSON.parse(fs.readFileSync('emb/index.json'));
console.log('index', JSON.stringify(idx).slice(0, 300));
const L = JSON.parse(fs.readFileSync('prices/onepiece.json'));
const files = fs.readdirSync('emb/onepiece'); let n = 0, zero = 0;
const vecs = [];
for (const f of files) { const b = fs.readFileSync('emb/onepiece/' + f); for (let o = 0; o < b.length; o += 520) { n++; const pid = b.readUInt32LE(o), s = b.readFloatLE(o + 4); if (!s) { zero++; continue; } const v = new Float32Array(512); for (let d = 0; d < 512; d++) v[d] = b.readInt8(o + 8 + d) * s; vecs.push([pid, v]); } }
console.log('cards', n, 'no picture', zero, 'files', files.length);
const dot = (a, b) => { let s = 0; for (let i = 0; i < 512; i++) s += a[i] * b[i]; return s; };
// nearest neighbours of a few cards: same character's other printings should come first
for (const [pid, v] of vecs.slice(0, 4)) {
  const near = vecs.filter(x => x[0] !== pid).map(([p, w]) => [p, dot(v, w)]).sort((a, b) => b[1] - a[1]).slice(0, 3);
  console.log(L.p[pid][1], '|', near.map(([p, s]) => L.p[p][1] + ' ' + s.toFixed(3)).join(' ; '), '| norm', dot(v, v).toFixed(3));
}

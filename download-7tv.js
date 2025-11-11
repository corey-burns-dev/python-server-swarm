// download-7tv.js
// Enhanced downloader: fetch global emotes from 7TV, BetterTTV (BTTV), and FrankerFaceZ (FFZ)
// Saves images in ./emotes and writes emotes/emotes.json mapping name -> filename

const fs = require('fs');
const path = require('path');
const https = require('https');

const OUT_DIR = path.resolve(__dirname, 'emotes');
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

function fetchJson(url) {
  return fetch(url).then(r => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  });
}

async function downloadTo(url, dest) {
  // If file exists and non-empty, skip
  try {
    if (fs.existsSync(dest) && fs.statSync(dest).size > 100) return true;
  } catch (e) {}

  // Try fetch API and fallback to https.get streaming
  try {
    const res = await fetch(url);
    if (!res.ok) return false;
    const buf = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync(dest, buf);
    return true;
  } catch (e) {
    // fallback
    return new Promise((resolve) => {
      const file = fs.createWriteStream(dest);
      https.get(url, (res) => {
        if (res.statusCode && res.statusCode >= 400) return resolve(false);
        res.pipe(file);
        file.on('finish', () => {
          file.close();
          resolve(true);
        });
      }).on('error', () => resolve(false));
    });
  }
}

async function gather7tv() {
  const url = 'https://7tv.io/v3/emote-sets/global';
  try {
    const data = await fetchJson(url);
    return (data.emotes || []).map(e => ({ name: e.name, url: `https://cdn.7tv.app/emote/${e.id}/4x.webp` }));
  } catch (e) {
    console.warn('7TV fetch failed:', e.message || e);
    return [];
  }
}

async function gatherBttv() {
  const url = 'https://api.betterttv.net/3/cached/emotes/global';
  try {
    const data = await fetchJson(url);
    return (data || []).map(e => ({ name: e.code, url: `https://cdn.betterttv.net/emote/${e.id}/3x` }));
  } catch (e) {
    console.warn('BTTV fetch failed:', e.message || e);
    return [];
  }
}

async function gatherFfz() {
  const url = 'https://api.frankerfacez.com/v1/set/global';
  try {
    const data = await fetchJson(url);
    const list = [];
    const sets = data.sets || {};
    for (const k of Object.keys(sets)) {
      const s = sets[k];
      const emotes = s.emoticons || s.emotes || [];
      for (const e of emotes) {
        if (!e.id || !e.name) continue;
        // CDN path by id
        list.push({ name: e.name, url: `https://cdn.frankerfacez.com/emote/${e.id}/4` });
      }
    }
    return list;
  } catch (e) {
    console.warn('FFZ fetch failed:', e.message || e);
    return [];
  }
}

function safeName(name) {
  return name.replace(/[^A-Za-z0-9_\-]/g, '_').replace(/_+/g, '_').slice(0, 160);
}

async function main() {
  console.log('Gathering emote lists...');
  const [a, b, c] = await Promise.all([gather7tv(), gatherBttv(), gatherFfz()]);
  let entries = [...a, ...b, ...c];

  // dedupe by lowercase name (prefer first seen order: 7TV, BTTV, FFZ)
  const map = new Map();
  for (const e of entries) {
    const key = e.name.toLowerCase();
    if (!map.has(key)) map.set(key, e.url);
  }

  const deduped = Array.from(map.entries()).map(([name, url]) => ({ name, url }));

  console.log(`Found ${deduped.length} unique emote names to attempt`);

  const emoteMap = {};
  const concurrency = 12;
  const batch = [];
  for (const item of deduped) {
    batch.push(item);
    if (batch.length >= concurrency) {
      await Promise.all(batch.map(x => processEmote(x, emoteMap)));
      batch.length = 0;
    }
  }
  if (batch.length) await Promise.all(batch.map(x => processEmote(x, emoteMap)));

  // Write emotes.json
  const outPath = path.join(OUT_DIR, 'emotes.json');
  fs.writeFileSync(outPath, JSON.stringify(emoteMap, null, 2), 'utf8');
  console.log('Wrote', outPath, Object.keys(emoteMap).length, 'entries');
}

async function processEmote(item, emoteMap) {
  const displayName = item.name;
  const base = safeName(displayName);
  // attempt common extensions/suffixes
  const candidates = [];
  // if url ends with known ext, try directly
  if (/\.(webp|png|gif|jpg)$/i.test(item.url)) {
    candidates.push(item.url);
  } else {
    // common CDN patterns
    candidates.push(item.url + '.webp');
    candidates.push(item.url + '.png');
    candidates.push(item.url);
  }

  for (const url of candidates) {
    const extMatch = url.match(/\.(webp|png|gif|jpg)(?:$|\?)/i);
    const ext = extMatch ? extMatch[1] : 'webp';
    let filename = `${base}.${ext}`;
    let dest = path.join(OUT_DIR, filename);
    // avoid collisions
    let i = 1;
    while (fs.existsSync(dest)) {
      filename = `${base}_${i}.${ext}`;
      dest = path.join(OUT_DIR, filename);
      i++;
    }
    try {
      const ok = await downloadTo(url, dest);
      if (ok) {
        emoteMap[displayName] = filename;
        console.log('[OK]', displayName, '->', filename);
        return;
      }
    } catch (e) {
      // ignore and try next
    }
  }
  console.log('[SKIP]', displayName);
}

main().catch(e => {
  console.error('Failed:', e);
  process.exit(1);
});

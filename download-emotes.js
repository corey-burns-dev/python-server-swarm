// download-emotes.js
// Downloads global emotes from 7TV, BTTV, and FFZ and writes emotes/emotes.json
// Usage: node download-emotes.js

const fs = require('fs');
const path = require('path');
// Node 18+ has global fetch; use it directly
const fetch = global.fetch;

const dir = path.join(__dirname, 'emotes');
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

const emoteMap = {};

async function download(url, filepath) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to download ${url} ${res.status}`);
  const buf = await res.arrayBuffer();
  fs.writeFileSync(filepath, Buffer.from(buf));
}

async function fetch7tv() {
  try {
    console.log('Fetching 7TV global emotes...');
    const res = await fetch('https://7tv.io/v3/emote-sets/global');
    if (!res.ok) throw new Error('7TV response not ok');
    const data = await res.json();
    if (data.emotes && Array.isArray(data.emotes)) {
      for (const emote of data.emotes) {
        if (emote.name && emote.id) {
          const filename = `${emote.id}.webp`;
          const url = `https://cdn.7tv.app/emote/${emote.id}/1x.webp`;
          try {
            await download(url, path.join(dir, filename));
            emoteMap[emote.name] = filename;
          } catch (e) {
            // skip failures
          }
        }
      }
    }
  } catch (e) {
    console.error('7TV fetch failed', e.message);
  }
}

async function fetchBTTV() {
  try {
    console.log('Fetching BTTV global emotes...');
    const res = await fetch('https://api.betterttv.net/3/cached/emotes/global');
    if (!res.ok) throw new Error('BTTV response not ok');
    const data = await res.json();
    for (const em of data) {
      const id = em.id;
      const name = em.code;
      const url = `https://cdn.betterttv.net/emote/${id}/3x`;
      const filename = `${id}.png`;
      try {
        await download(url, path.join(dir, filename));
        emoteMap[name] = filename;
      } catch (e) {
        // try webp fallback
        try {
          const url2 = `https://cdn.betterttv.net/emote/${id}/1x`;
          await download(url2, path.join(dir, filename));
          emoteMap[name] = filename;
        } catch (e2) {
          // skip
        }
      }
    }
  } catch (e) {
    console.error('BTTV fetch failed', e.message);
  }
}

async function fetchFFZ() {
  try {
    console.log('Fetching FFZ global emotes...');
    // Get global emote set id
    const r = await fetch('https://api.frankerfacez.com/v1/emoticons');
    if (!r.ok) throw new Error('FFZ response not ok');
    const data = await r.json();
    if (data && data.default_sets) {
      // default_sets is an array of set ids
      for (const setId of data.default_sets) {
        // setId may be numeric
        const setRes = await fetch(`https://api.frankerfacez.com/v1/set/${setId}`);
        if (!setRes.ok) continue;
        const setData = await setRes.json();
        if (setData && setData.set && setData.set.emoticons) {
          for (const em of setData.set.emoticons) {
            const urls = em.urls;
            const name = em.name;
            // pick the highest available size
            const sizes = Object.keys(urls).map(Number).sort((a,b)=>b-a);
            const first = sizes[0];
            const url = `https:${urls[first]}`;
            const ext = path.extname(url).split('?')[0] || '.png';
            const filename = `${em.id}${ext}`;
            try {
              await download(url, path.join(dir, filename));
              emoteMap[name] = filename;
            } catch (e) {
              // skip
            }
          }
        }
      }
    }
  } catch (e) {
    console.error('FFZ fetch failed', e.message);
  }
}

(async () => {
  await fetch7tv();
  await fetchBTTV();
  await fetchFFZ();
  fs.writeFileSync(path.join(dir, 'emotes.json'), JSON.stringify(emoteMap, null, 2));
  console.log('Downloaded emotes:', Object.keys(emoteMap).length);
})();

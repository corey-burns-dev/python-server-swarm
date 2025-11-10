// download-7tv.js
const fs = require('fs');
const https = require('https');
const path = require('path');

async function download7TV() {
  const response = await fetch('https://7tv.io/v3/emote-sets/global');
  const data = await response.json();
  
  const dir = './emotes';
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  
  for (const emote of data.emotes) {
    const url = `https://cdn.7tv.app/emote/${emote.id}/1x.webp`;
    const filepath = path.join(dir, `${emote.id}.webp`);
    
    https.get(url, (res) => {
      const stream = fs.createWriteStream(filepath);
      res.pipe(stream);
      stream.on('finish', () => {
        console.log(`Downloaded: ${emote.name}`);
        stream.close();
      });
    });
  }
  
  // Save emote map
  const emoteMap = {};
  data.emotes.forEach(e => emoteMap[e.name] = `${e.id}.webp`);
  fs.writeFileSync(path.join(dir, 'emotes.json'), JSON.stringify(emoteMap, null, 2));
}

download7TV();
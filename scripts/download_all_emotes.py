#!/usr/bin/env python3
"""Download common global emotes from 7TV, BTTV (BetterTTV), and FFZ (FrankerFaceZ).

Saves images under ./emotes/ and writes an emotes/emotes.json mapping
emote name -> filename.

Usage:
    python scripts/download_all_emotes.py

Options:
    --out-dir DIR      Output directory (default: ./emotes)
    --concurrency N    Number of concurrent downloads (default: 12)
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import aiohttp

# Known endpoints
SEVENTV_GLOBAL = "https://7tv.io/v3/emote-sets/global"
BTTV_GLOBAL = "https://api.betterttv.net/3/cached/emotes/global"
FFZ_GLOBAL = "https://api.frankerfacez.com/v1/set/global"

VALID_EXT = ["webp", "png", "gif", "jpg"]

async def fetch_json(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            return await resp.json()
    except Exception as e:
        print(f"[ERR] Fetch JSON failed for {url}: {e}")
        return None


def safe_name(name: str) -> str:
    # sanitize emote name to a filename friendly representation
    name = name.strip()
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name[:180]


async def download_file(session: aiohttp.ClientSession, url: str, dest: Path) -> bool:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                return False
            data = await resp.read()
            dest.write_bytes(data)
            return True
    except Exception:
        return False


async def gather_7tv(session: aiohttp.ClientSession) -> List[Tuple[str, str]]:
    out = []
    data = await fetch_json(session, SEVENTV_GLOBAL)
    if not data:
        return out
    emotes = data.get("emotes") or []
    for e in emotes:
        # e: { id, name, mime, host? }
        eid = e.get("id")
        name = e.get("name")
        if not eid or not name:
            continue
        # prefer webp 4x
        url = f"https://cdn.7tv.app/emote/{eid}/4x.webp"
        out.append((name, url))
    return out


async def gather_bttv(session: aiohttp.ClientSession) -> List[Tuple[str, str]]:
    out = []
    data = await fetch_json(session, BTTV_GLOBAL)
    if not data:
        return out
    for e in data:
        # e: { id, code }
        eid = e.get("id")
        code = e.get("code")
        if not eid or not code:
            continue
        # CDN: https://cdn.betterttv.net/emote/{id}/3x
        url = f"https://cdn.betterttv.net/emote/{eid}/3x"
        # try webp, png fallback will be attempted at download step
        out.append((code, url))
    return out


async def gather_ffz(session: aiohttp.ClientSession) -> List[Tuple[str, str]]:
    out = []
    data = await fetch_json(session, FFZ_GLOBAL)
    if not data:
        return out
    # FFZ global returns a "sets" map with emote lists
    sets = data.get("sets") or {}
    for setid, s in sets.items():
        emotes = s.get("emoticons") or s.get("emotes") or []
        for e in emotes:
            # e may contain id, name, urls
            eid = e.get("id")
            name = e.get("name")
            # FFZ CDN: https://cdn.frankerfacez.com/emote/{id}/4
            if eid and name:
                url = f"https://cdn.frankerfacez.com/emote/{eid}/4"
                out.append((name, url))
    return out


async def download_all(out_dir: Path, concurrency: int = 12):
    out_dir.mkdir(parents=True, exist_ok=True)
    emote_map: Dict[str, str] = {}
    seen_filenames = set()

    async with aiohttp.ClientSession() as session:
        print("Gathering emote lists from 7TV, BTTV, FFZ...")
        tasks = await asyncio.gather(
            gather_7tv(session),
            gather_bttv(session),
            gather_ffz(session),
        )
        entries: List[Tuple[str, str]] = []
        for part in tasks:
            entries.extend(part)

        # dedupe by lowercase name (prefer first occurrence)
        deduped: Dict[str, Tuple[str,str]] = {}
        for name, url in entries:
            key = name.lower()
            if key not in deduped:
                deduped[key] = (name, url)

        entries = list(deduped.values())

        print(f"Found {len(entries)} unique emotes to try download")

        sem = asyncio.Semaphore(concurrency)

        async def worker(name: str, url_base: str):
            async with sem:
                safe = safe_name(name)
                # choose filename base, avoid collisions
                base = f"{safe}"
                filename = None
                # try a number of candidate urls/extensions/sizes
                tried_urls = []
                # If url_base already contains extension, try it directly
                candidates = []
                # common attempts
                for ext in ["webp", "png", "gif", "jpg"]:
                    # append extension if not present
                    if url_base.endswith(ext):
                        candidates.append(url_base)
                    else:
                        candidates.append(f"{url_base}.{ext}")
                # sizes: some CDNs accept numeric path suffixes (4,3,2,1)
                extra = []
                for c in candidates:
                    extra.append(c)
                    extra.append(c + "/")
                candidates = extra

                # Try each candidate until download succeeds
                for cand in candidates:
                    tried_urls.append(cand)
                    # pick extension
                    m = re.search(r"\\.(webp|png|gif|jpg)($|\\?)", cand, re.IGNORECASE)
                    ext = m.group(1) if m else "webp"
                    out_name = f"{base}.{ext}"
                    # avoid duplicate filename collisions by suffixing
                    i = 1
                    final = out_name
                    while final in seen_filenames:
                        final = f"{base}_{i}.{ext}"
                        i += 1
                    dest = out_dir / final
                    ok = await download_file(session, cand, dest)
                    if ok and dest.exists() and dest.stat().st_size > 100:
                        seen_filenames.add(final)
                        emote_map[name] = final
                        print(f"[OK] {name} -> {final}")
                        return
                print(f"[SKIP] {name} (tried {len(tried_urls)} urls)")

        # schedule workers
        workers = [worker(name, url) for name, url in entries]
        # run in batches to avoid huge memory spike
        BATCH = 200
        for i in range(0, len(workers), BATCH):
            batch = workers[i:i+BATCH]
            await asyncio.gather(*batch)

    # write out emotes.json
    out_json = out_dir / 'emotes.json'
    with out_json.open('w', encoding='utf-8') as f:
        json.dump(emote_map, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_json} ({len(emote_map)} entries)")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', default='emotes', help='output directory')
    parser.add_argument('--concurrency', type=int, default=12, help='concurrent downloads')
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    try:
        asyncio.run(download_all(out_dir, args.concurrency))
    except KeyboardInterrupt:
        print('Aborted')


if __name__ == '__main__':
    main()

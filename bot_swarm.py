# bot_swarm.py
import asyncio
import json
import os
import random
import time
import aiohttp
from faker import Faker
import socketio
import re  # for emote parsing

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000")
LM_API     = os.getenv("LM_API", "http://localhost:1234/v1/chat/completions")
MODEL      = os.getenv("LM_MODEL", "lmstudio-community/Meta-Llama-3-8B-Instruct")

ROOM_ID    = "test-room-123"
NUM_BOTS   = 12
MAX_TOKENS = 60
TEMPERATURE = 0.85

fake = Faker()

PERSONAS = [
    "Alex, 25, software dev from Kitchener, loves sci-fi and memes",
    "Sam, 19, university student, obsessed with K-pop and food pics",
    "Jordan, 32, graphic designer, into hiking and craft beer",
    "Mia, 27, nurse, enjoys yoga and true-crime podcasts",
    "Liam, 22, barista, plays guitar and follows indie bands",
    "Emma, 30, data scientist, runs marathons and bakes sourdough",
    "Tyler, 28, gamer, streams on Twitch, loves RPGs and pizza",
    "Zoe, 24, artist, paints landscapes, into meditation and tea",
    "Ryan, 35, chef, experiments with fusion cuisine, watches cooking shows",
    "Ava, 21, musician, plays piano, loves jazz and late-night talks",
    "Noah, 26, entrepreneur, builds apps, into crypto and startups",
    "Sophia, 29, teacher, loves history, reads fantasy novels",
    "Ethan, 31, photographer, travels, captures street art",
    "Isabella, 23, dancer, practices ballet, follows fashion trends",
    "Mason, 27, mechanic, fixes cars, enjoys motorsports",
    "Harper, 33, writer, pens mystery novels, loves coffee shops",
    "Logan, 20, athlete, plays soccer, studies sports science",
    "Ella, 26, environmentalist, volunteers, hikes and camps",
    "Jackson, 34, architect, designs sustainable buildings",
    "Aria, 22, streamer, plays games, chats with fans online",
]

# ----------------------------------------------------------------------
# 7TV Emotes
# ----------------------------------------------------------------------
SEVENTV_EMOTES = {}  # name -> id

async def load_7tv_emotes():
    global SEVENTV_EMOTES
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://7tv.io/v3/emote-sets/global") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "emotes" in data:
                        for emote in data["emotes"]:
                            if "name" in emote and "id" in emote:
                                SEVENTV_EMOTES[emote["name"]] = emote["id"]
                    print(f"Loaded {len(SEVENTV_EMOTES)} 7TV emotes with IDs")
                else:
                    print("Failed to load 7TV emotes")
                    # Fallback
                    SEVENTV_EMOTES = {
                        "PogChamp": "01FAGRADQ00008E6R5BC5KRVKP",
                        "Kappa": "01FAGRAEQ00008E6R5BC5KRVKR",
                        "LUL": "01FAGRADQ00008E6R5BC5KRVKR",
                        "OMEGALUL": "01FAGRADQ00008E6R5BC5KRVKS",
                        "PepeLaugh": "01FAGRADQ00008E6R5BC5KRVKT",
                        "monkaS": "01FAGRADQ00008E6R5BC5KRVKU"
                    }
    except Exception as e:
        print(f"Error loading 7TV emotes: {e}")
        SEVENTV_EMOTES = {
            "PogChamp": "01FAGRADQ00008E6R5BC5KRVKP",
            "Kappa": "01FAGRAEQ00008E6R5BC5KRVKR",
            "LUL": "01FAGRADQ00008E6R5BC5KRVKR",
            "OMEGALUL": "01FAGRADQ00008E6R5BC5KRVKS",
            "PepeLaugh": "01FAGRADQ00008E6R5BC5KRVKT",
            "monkaS": "01FAGRADQ00008E6R5BC5KRVKU"
        }

def get_emote_url(name):
    """Get 7TV CDN URL for emote (1x size for chat)."""
    # Static ID for global emotes (or fetch dynamically if needed)
    return f"https://static-cdn.jtvnw.net/emoticons/v2/{name}/default/dark/1.0"

# ----------------------------------------------------------------------
class ChatBot:
    def __init__(self, sid: str, name: str, persona: str):
        self.sid = sid
        self.name = name
        self.persona = persona
        self.history = []
        self.speed = random.uniform(3.0, 8.0)  # Slower responses
        self.bot_sio = None

    async def _call_lm(self, prompt: str) -> str:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": f"You are {self.persona}. Chat like in a live Twitch/Kick stream: keep responses VERY short (1 sentence max), use lots of emojis, abbreviations, be casual and reactive. No walls of text!"},
                *self.history,
                {"role": "user", "content": prompt}
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "stream": False
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LM_API, json=payload) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        return f"(LM error {resp.status})"
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                return f"(LM failed: {e})"

    async def send(self, text: str):
        print(f"{self.name} → {text}")
        if self.bot_sio and self.bot_sio.connected:
            await self.bot_sio.emit("bot_message", {
                "user": self.name,
                "text": text,
                "room": ROOM_ID
            })

    async def think_and_reply(self, room_history: list):
        recent = "\n".join(f"{m['user']}: {m['text']}" for m in room_history[-8:])
        prompt = f"""Recent chat:
{recent}

Reply as {self.name} (you are {self.persona}). Chat like in a live Twitch/Kick stream: keep responses VERY short (1 sentence max), use lots of emojis, abbreviations, be casual and reactive. No walls of text!"""

        # Chance for quick reactions
        if random.random() < 0.4:
            reactions = ["lol", "😂", "nice!", "🤔", "agree", "👍", "omg", "😮", "cool", "haha"]
            reply = random.choice(reactions)
        elif "/joke" in recent.lower():
            reply = f"{self.name} tells a joke: Why don't scientists trust atoms? Because they make up everything! 😂"
        elif "/help" in recent.lower():
            reply = f"{self.name} says: I'm here to chat! Try asking about {self.persona.split(',')[2] if len(self.persona.split(',')) > 2 else 'anything'} or use /joke for laughs!"
        elif "/roll" in recent.lower():
            roll = random.randint(1, 20)
            reply = f"{self.name} rolls a d20: {roll}! {'Critical hit!' if roll == 20 else 'Nice roll!' if roll > 15 else 'Oof.'}"
        else:
            reply = await self._call_lm(prompt)

        # Add random 7TV emote (40% chance)
        if SEVENTV_EMOTES and random.random() < 0.4:
            emote = random.choice(list(SEVENTV_EMOTES.keys()))
            reply += f" {emote}"

        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": reply})
        await self.send(reply)

# ----------------------------------------------------------------------
room_messages: list[dict] = []
bots: list[ChatBot] = []

async def spawn_bot(idx: int):
    name = f"{fake.first_name()}{random.randint(10,99)}"
    sid = f"bot_{idx}_{int(time.time())}"
    persona = random.choice(PERSONAS)

    bot = ChatBot(sid, name, persona)
    bots.append(bot)

    bot_sio = socketio.AsyncClient()
    bot.bot_sio = bot_sio

    @bot_sio.event
    async def connect():
        print(f"{name} connected")
        await bot_sio.emit("start", {"sid": sid, "system": f"You are {persona}"})
        await bot_sio.emit("join", {"room": ROOM_ID, "user": name})

    @bot_sio.event
    async def disconnect():
        print(f"{name} disconnected")

    @bot_sio.on("message")
    async def on_message(data):
        msg = {"user": data["user"], "text": data["text"]}
        room_messages.append(msg)
        if len(room_messages) > 20:
            room_messages.pop(0)

        bot_names = [b.name for b in bots]
        if data["user"] in bot_names + ["AI Assistant"] and random.random() > 0.2:
            return

        if random.random() < 0.1:  # Less frequent replies
            await bot_sio.emit("typing", {"room": ROOM_ID, "user": bot.name})
            await asyncio.sleep(random.uniform(bot.speed, bot.speed + 3.0))  # Longer delay
            await bot.think_and_reply(room_messages)
            await bot_sio.emit("stop_typing", {"room": ROOM_ID, "user": bot.name})

    try:
        await bot_sio.connect(SERVER_URL)
        await bot_sio.emit("start", {"sid": sid, "system": f"You are {persona}"})
        await bot_sio.emit("join", {"room": ROOM_ID, "user": name})
        print(f"Bot {name} joined")
        await bot_sio.wait()  # Keeps this bot alive
    except Exception as e:
        print(f"Bot {name} failed: {e}")

async def seed_conversation():
    await asyncio.sleep(5)  # Longer initial delay
    if bots:
        starter = random.choice(bots)
        await starter.send("Hey everyone! What's the vibe today? [sun emoji]")
        print("Seeded conversation")

async def auto_seed_loop():
    while True:
        await asyncio.sleep(random.uniform(180, 600))  # Less frequent auto-seeding
        if bots:
            bot = random.choice(bots)
            prompt = "Generate a very short, casual message to keep the conversation going. Like a Twitch chat message: 1 sentence max, emojis ok."
            reply = await bot._call_lm(prompt)
            await bot.send(reply)

async def main():
    print(f"Starting swarm: {NUM_BOTS} bots → {ROOM_ID}")

    await load_7tv_emotes()  # Load emotes first

    print("Spawning bots...")
    for i in range(NUM_BOTS):
        asyncio.create_task(spawn_bot(i))

    await seed_conversation()
    asyncio.create_task(auto_seed_loop())

    try:
        while True:
            await asyncio.sleep(90)
            alive = sum(1 for b in bots if b.bot_sio and b.bot_sio.connected)
            print(f"Swarm alive: {alive}/{len(bots)} bots")
    except KeyboardInterrupt:
        print("\nShutting down…")

if __name__ == "__main__":
    asyncio.run(main())
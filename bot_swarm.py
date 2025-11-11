import asyncio
import json
import os
import random
import time
import aiohttp
from faker import Faker
import socketio
import re

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
    "sarcastic weeb who roasts people playfully and loves anime",
    "hype beast who gets excited about everything and spams emotes",
    "lurker who rarely talks but drops fire comments",
    "wholesome viewer who supports everyone with positive vibes",
    "toxic troll who lightly roasts but keeps it funny",
    "meme lord who references old and new memes constantly",
    "backseat gamer who gives unsolicited advice",
    "coomer who simps for waifus and vtubers unironically",
    "pepega viewer who asks obvious questions",
    "based gigachad who drops hot takes confidently",
    "weeb degenerate who discusses anime waifus tier lists",
    "normie who doesn't get chat culture but tries",
]

# ----------------------------------------------------------------------
# TWITCH EMOTES & SLANG
# ----------------------------------------------------------------------
SEVENTV_EMOTES = {}

# Common Twitch slang and abbreviations
TWITCH_SLANG = [
    "poggers", "based", "cringe", "copium", "hopium", "kekw",
    "sadge", "monkas", "pepega", "5head", "WeirdChamp", "PogU",
    "BOOBA", "Aware", "forsen", "xqcL", "GIGACHAD", "ICANT"
]

# Roast templates
ROASTS = [
    "bro {target} really said that 💀",
    "{target} actual pepega moment",
    "nah {target} you're wildin",
    "{target} take the L my guy",
    "least delusional {target} take",
    "{target} bro fell off 😭",
    "{target} actual NPC dialogue",
]

# Reactions to streamer actions (simulated)
STREAMER_REACTIONS = [
    "NO WAY", "CAUGHT IN 4K", "ACTUAL GOD GAMER", "HE CANT KEEP GETTING AWAY WITH THIS",
    "SCRIPTWRITER BUFF", "RIGGED", "DESERVED", "UNDESERVED", "GIGACHAD MOMENT",
]

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
                    print(f"Loaded {len(SEVENTV_EMOTES)} 7TV emotes")
                else:
                    print("Failed to load 7TV emotes, using fallback")
                    _load_fallback_emotes()
    except Exception as e:
        print(f"Error loading 7TV emotes: {e}")
        _load_fallback_emotes()

def _load_fallback_emotes():
    global SEVENTV_EMOTES
    SEVENTV_EMOTES = {
        "PogChamp": "1", "Kappa": "2", "LUL": "3", "OMEGALUL": "4",
        "PepeLaugh": "5", "monkaS": "6", "KEKW": "7", "Sadge": "8",
        "POGGERS": "9", "EZ": "10", "Clap": "11", "FeelsStrongMan": "12",
        "BibleThump": "13", "PepeHands": "14", "widePeepoHappy": "15",
        "Pog": "16", "monkaW": "17", "BOOBA": "18", "Aware": "19",
        "GIGACHAD": "20", "Clueless": "21", "Copium": "22", "Susge": "23"
    }

# ----------------------------------------------------------------------
class ChatBot:
    def __init__(self, sid: str, name: str, persona: str):
        self.sid = sid
        self.name = name
        self.persona = persona
        self.history = []
        self.speed = random.uniform(2.0, 8.0)  # Typing speed variation
        self.bot_sio = None
        self.msg_count = 0
        self.last_msg_time = 0
        self.roast_cooldown = 0
        
        # Personality traits (affects behavior)
        self.chattiness = random.uniform(0.05, 0.25)  # How often they respond
        self.emote_rate = random.uniform(0.3, 0.8)   # How often they use emotes
        self.roast_tendency = random.uniform(0.1, 0.4)  # How often they roast

    async def _call_lm(self, prompt: str) -> str:
        try:
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(LM_API, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data["choices"][0]["message"]["content"].strip()
                        return reply
        except Exception as e:
            print(f"LM call failed for {self.name}: {e}")
        
        # Fallback responses
        return self._generate_fallback()

    def _generate_fallback(self):
        """Generate realistic Twitch-style responses without LM"""
        responses = [
            "lol", "lmao", "true", "real", "based", "W", "L", "fr fr",
            "no cap", "on god", "facts", "this", "so true", "💀",
            "😭", "🔥", "valid", "ratio", "ong", "deadass"
        ]
        
        # Add emote to some responses
        if random.random() < self.emote_rate and SEVENTV_EMOTES:
            emote = random.choice(list(SEVENTV_EMOTES.keys()))
            if random.random() < 0.5:
                return f"{random.choice(responses)} {emote}"
            return emote
        
        return random.choice(responses)

    async def send(self, text: str):
        self.msg_count += 1
        self.last_msg_time = time.time()
        print(f"{self.name} → {text}")
        if self.bot_sio and self.bot_sio.connected:
            await self.bot_sio.emit("bot_message", {
                "user": self.name,
                "text": text,
                "room": ROOM_ID
            })

    def should_respond(self, room_history: list) -> bool:
        """Smarter response logic"""
        if not room_history:
            return False
        
        recent = room_history[-3:]
        
        # Don't respond to own messages
        if any(m["user"] == self.name for m in recent):
            return False
        
        # More likely to respond if mentioned
        for msg in recent:
            if self.name.lower() in msg["text"].lower():
                return random.random() < 0.7
        
        # Check cooldown (don't spam)
        if time.time() - self.last_msg_time < 5:
            return False
        
        # Random based on chattiness
        return random.random() < self.chattiness

    async def generate_roast(self, target: str) -> str:
        """Generate a playful roast"""
        template = random.choice(ROASTS)
        roast = template.format(target=target)
        
        # Add emote
        if random.random() < 0.7 and SEVENTV_EMOTES:
            emotes = ["KEKW", "PepeLaugh", "EZ", "OMEGALUL", "LUL"]
            available = [e for e in emotes if e in SEVENTV_EMOTES]
            if available:
                roast += f" {random.choice(available)}"
        
        return roast

    async def think_and_reply(self, room_history: list):
        recent = room_history[-6:]
        last_msg = recent[-1] if recent else None
        
        # Check for roast opportunity
        if (last_msg and 
            last_msg["user"] != self.name and 
            random.random() < self.roast_tendency and
            time.time() - self.roast_cooldown > 30):
            self.roast_cooldown = time.time()
            reply = await self.generate_roast(last_msg["user"])
            await self.send(reply)
            return
        
        # Check for commands
        if last_msg and "/joke" in last_msg["text"].lower():
            jokes = [
                "why did the chicken cross the road? to get to the other side KEKW",
                "what do you call a fake noodle? an impasta 💀",
                "im not funny pepeLaugh",
            ]
            reply = random.choice(jokes)
            await self.send(reply)
            return
        
        if last_msg and "/roll" in last_msg["text"].lower():
            roll = random.randint(1, 100)
            reply = f"rolled {roll}"
            if roll > 95:
                reply += " GIGACHAD"
            elif roll < 10:
                reply += " Sadge"
            await self.send(reply)
            return
        
        # Build context for LM
        chat_context = "\n".join(f"{m['user']}: {m['text']}" for m in recent)
        
        prompt = f"""You are {self.name}, a Twitch chatter. Persona: {self.persona}

Recent chat:
{chat_context}

Reply with ONE short message (max 10 words). Be casual, use internet slang, be reactive. Examples:
- "lmao fr"
- "based take"
- "nah you trippin"
- "W streamer"
- "this guy actually good"

Your response:"""

        # Try LM, fallback to template
        reply = await self._call_lm(prompt)
        
        # Clean up LM response (remove quotes, newlines, etc)
        reply = re.sub(r'^["\'`]|["\'`]$', '', reply)
        reply = reply.split('\n')[0].strip()
        
        # Limit length
        if len(reply) > 100:
            reply = self._generate_fallback()
        
        # Add emote based on emote_rate
        if random.random() < self.emote_rate and SEVENTV_EMOTES:
            emote = random.choice(list(SEVENTV_EMOTES.keys()))
            if random.random() < 0.4:  # 40% replace with just emote
                reply = emote
            else:  # 60% append emote
                reply += f" {emote}"
        
        # Occasionally add Twitch slang
        if random.random() < 0.2:
            reply += f" {random.choice(TWITCH_SLANG)}"
        
        await self.send(reply)

# ----------------------------------------------------------------------
room_messages: list[dict] = []
bots: list[ChatBot] = []

async def spawn_bot(idx: int):
    name = f"{fake.first_name()}{random.randint(10,999)}"
    sid = f"bot_{idx}_{int(time.time())}"
    persona = random.choice(PERSONAS)

    bot = ChatBot(sid, name, persona)
    bots.append(bot)

    bot_sio = socketio.AsyncClient()
    bot.bot_sio = bot_sio

    @bot_sio.event
    async def connect():
        print(f"{name} connected as: {persona}")
        await bot_sio.emit("start", {"sid": sid, "system": f"You are {persona}"})
        await bot_sio.emit("join", {"room": ROOM_ID, "user": name})

    @bot_sio.event
    async def disconnect():
        print(f"{name} disconnected")

    @bot_sio.on("message")
    async def on_message(data):
        msg = {"user": data["user"], "text": data["text"]}
        room_messages.append(msg)
        
        # Keep last 50 messages
        if len(room_messages) > 50:
            room_messages.pop(0)

        # Smart response logic
        if not bot.should_respond(room_messages):
            return

        # Show typing indicator
        await bot_sio.emit("typing", {"room": ROOM_ID, "user": bot.name})
        
        # Realistic typing delay (reading + typing time)
        read_time = len(data["text"]) * 0.03  # Time to read message
        type_time = random.uniform(bot.speed * 0.5, bot.speed * 1.5)
        await asyncio.sleep(read_time + type_time)
        
        await bot.think_and_reply(room_messages)
        await bot_sio.emit("stop_typing", {"room": ROOM_ID, "user": bot.name})

    try:
        await bot_sio.connect(SERVER_URL)
        await bot_sio.emit("start", {"sid": sid, "system": f"You are {persona}"})
        await bot_sio.emit("join", {"room": ROOM_ID, "user": name})
        print(f"Bot {name} spawned")
        await bot_sio.wait()
    except Exception as e:
        print(f"Bot {name} error: {e}")

async def seed_conversation():
    """Start initial conversation"""
    await asyncio.sleep(5)
    if bots:
        starter = random.choice(bots)
        starters = [
            "yo whats good", "anyone here?", "dead chat", "first KEKW",
            "hi chat", "what we watchin", "poggers stream", "lets goooo"
        ]
        msg = random.choice(starters)
        if SEVENTV_EMOTES and random.random() < 0.5:
            msg += f" {random.choice(list(SEVENTV_EMOTES.keys()))}"
        await starter.send(msg)

async def periodic_activity():
    """Bots occasionally send unprompted messages"""
    while True:
        await asyncio.sleep(random.uniform(45, 120))
        
        if not bots or not room_messages:
            continue
        
        # Pick a chatty bot
        active_bots = [b for b in bots if b.chattiness > 0.15]
        if not active_bots:
            continue
        
        bot = random.choice(active_bots)
        
        actions = [
            ("streamer_reaction", 0.3),
            ("random_comment", 0.5),
            ("copypasta", 0.1),
            ("emote_spam", 0.1),
        ]
        
        action = random.choices([a[0] for a in actions], [a[1] for a in actions])[0]
        
        if action == "streamer_reaction":
            msg = random.choice(STREAMER_REACTIONS)
            if SEVENTV_EMOTES:
                msg += f" {random.choice(list(SEVENTV_EMOTES.keys()))}"
            await bot.send(msg)
        
        elif action == "random_comment":
            comments = [
                "this stream actually good", "based content", "W streamer fr",
                "chat moving so fast", "anyone else seeing this", "clip that",
                "POV:", "rare W", "common L", "im done 💀"
            ]
            await bot.send(random.choice(comments))
        
        elif action == "copypasta":
            if SEVENTV_EMOTES:
                emote = random.choice(list(SEVENTV_EMOTES.keys()))
                await bot.send(f"{emote} " * random.randint(3, 7))
        
        elif action == "emote_spam":
            if SEVENTV_EMOTES:
                emote = random.choice(list(SEVENTV_EMOTES.keys()))
                await bot.send(emote * random.randint(2, 5))

async def main():
    print(f"🤖 Starting bot swarm: {NUM_BOTS} bots → {ROOM_ID}")
    print(f"🎯 Server: {SERVER_URL}")
    
    await load_7tv_emotes()
    
    print("🚀 Spawning bots...")
    for i in range(NUM_BOTS):
        asyncio.create_task(spawn_bot(i))
        await asyncio.sleep(0.5)  # Stagger spawns
    
    await seed_conversation()
    asyncio.create_task(periodic_activity())
    
    try:
        while True:
            await asyncio.sleep(60)
            alive = sum(1 for b in bots if b.bot_sio and b.bot_sio.connected)
            total_msgs = sum(b.msg_count for b in bots)
            print(f"📊 Status: {alive}/{len(bots)} bots | {total_msgs} messages sent")
    except KeyboardInterrupt:
        print("\n👋 Shutting down swarm...")

if __name__ == "__main__":
    asyncio.run(main())
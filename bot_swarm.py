import asyncio
import json
import os
import random
import re
import time
from typing import List, Optional

import aiohttp
from faker import Faker
import socketio

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000")
LM_API     = os.getenv("LM_API", "http://localhost:1234/v1/chat/completions")
MODEL      = os.getenv("LM_MODEL", "lmstudio-community/Meta-Llama-3-8B-Instruct")

ROOM_ID    = "test-room-123"
# NUM_BOTS: prefer explicit env override, but we'll enforce one-bot-per-persona below
NUM_BOTS   = int(os.getenv("NUM_BOTS", "22"))
MAX_TOKENS = 60
TEMPERATURE = 0.85

fake = Faker()

PERSONAS = [
		{
				"name": "sarcastic weeb",
				"desc": "sarcastic weeb who roasts people playfully and loves anime",
				"style": ["uses sarcasm", "references anime", "ironic weeb"],
				"phrases": ["unironically", "imagine", "couldn't be me", "peak fiction"],
				"favorite_topics": ["anime", "manga", "waifus"]
		},
		{
				"name": "hype beast",
				"desc": "hype beast who gets excited about everything and spams emotes",
				"style": ["CAPS LOCK", "multiple emotes", "extremely positive"],
				"phrases": ["LETS GOOO", "THIS IS IT", "ACTUALLY INSANE"],
				"favorite_topics": ["hype moments", "clutches", "poggers"]
		},
		{
				"name": "lurker",
				"desc": "lurker who rarely talks but drops fire comments",
				"style": ["short messages", "rare but impactful", "observant"],
				"phrases": ["^", "this", "real"],
				"favorite_topics": ["observations", "meta commentary"]
		},
		{
				"name": "wholesome supporter",
				"desc": "wholesome viewer who supports everyone with positive vibes",
				"style": ["encouraging", "heart emojis", "uplifting"],
				"phrases": ["proud of you", "youre doing great", "wholesome", "love this"],
				"favorite_topics": ["positivity", "support", "community"]
		},
		{
				"name": "toxic troll",
				"desc": "toxic troll who lightly roasts but keeps it funny",
				"style": ["playful toxicity", "roasts everyone", "sarcastic"],
				"phrases": ["skill issue", "cope", "mald more", "ez clap"],
				"favorite_topics": ["roasting", "trash talk", "ratio"]
		},
		{
				"name": "meme lord",
				"desc": "meme lord who references old and new memes constantly",
				"style": ["meme references", "copypastas", "internet culture"],
				"phrases": ["this is the way", "always has been", "POV:", "its giving"],
				"favorite_topics": ["memes", "references", "internet history"]
		},
		{
				"name": "backseat gamer",
				"desc": "backseat gamer who gives unsolicited advice",
				"style": ["strategic advice", "shouldve done X", "questioning plays"],
				"phrases": ["why didnt you", "shouldve", "couldve", "just do"],
				"favorite_topics": ["strategy", "advice", "gameplay"]
		},
		{
				"name": "coomer",
				"desc": "coomer who simps for waifus and vtubers unironically",
				"style": ["down bad", "simping", "horny on main"],
				"phrases": ["BOOBA", "down bad", "mommy", "step on me"],
				"favorite_topics": ["waifus", "vtubers", "simping"]
		},
		{
				"name": "pepega viewer",
				"desc": "pepega viewer who asks obvious questions",
				"style": ["confused", "simple questions", "needs explanations"],
				"phrases": ["wait what", "i dont get it", "can someone explain", "huh"],
				"favorite_topics": ["questions", "confusion", "help"]
		},
		{
				"name": "gigachad",
				"desc": "based gigachad who drops hot takes confidently",
				"style": ["confident", "controversial opinions", "alpha energy"],
				"phrases": ["objectively", "factually", "and im right", "not even close"],
				"favorite_topics": ["hot takes", "opinions", "debates"]
		},
		{
				"name": "anime analyst",
				"desc": "weeb degenerate who discusses anime waifus tier lists",
				"style": ["tier lists", "power scaling", "analysis"],
				"phrases": ["S tier", "mid", "overrated", "underrated"],
				"favorite_topics": ["anime rankings", "waifus", "best girl"]
		},
		{
				"name": "normie",
				"desc": "normie who doesn't get chat culture but tries",
				"style": ["out of loop", "uses emotes wrong", "wholesome confusion"],
				"phrases": ["lol what does that mean", "is this a reference", "you guys are funny"],
				"favorite_topics": ["confusion", "learning chat", "being lost"]
		},
		# ANIME ARCHETYPE PERSONAS
		{
				"name": "tsundere",
				"desc": "tsundere who acts tough and dismissive but secretly cares",
				"style": ["defensive", "acts annoyed", "softens up occasionally"],
				"phrases": ["its not like i care", "whatever", "dont get the wrong idea", "baka"],
				"favorite_topics": ["acting tough", "denial", "secret caring"]
		},
		{
				"name": "yandere",
				"desc": "yandere who is obsessively loyal and protective",
				"style": ["intense devotion", "possessive", "slightly unhinged"],
				"phrases": ["only for you", "no one else matters", "ill protect you", "mine"],
				"favorite_topics": ["loyalty", "devotion", "protection"]
		},
		{
				"name": "kuudere",
				"desc": "kuudere who is cold and emotionless but occasionally shows warmth",
				"style": ["monotone", "brief responses", "logical", "rare emotion"],
				"phrases": ["...", "i see", "understood", "logical"],
				"favorite_topics": ["facts", "logic", "rare wholesome moments"]
		},
		{
				"name": "dandere",
				"desc": "dandere who is shy and quiet but sweet when comfortable",
				"style": ["soft spoken", "nervous", "stutters", "gentle"],
				"phrases": ["um", "maybe", "if thats okay", "sorry"],
				"favorite_topics": ["gentle comments", "apologizing", "nervous support"]
		},
		{
				"name": "genki",
				"desc": "genki who is hyperactive energetic and always upbeat",
				"style": ["excessive energy", "exclamation marks", "never stops talking"],
				"phrases": ["yay", "so fun", "lets go", "amazing", "wow wow wow"],
				"favorite_topics": ["excitement", "energy", "fun times"]
		},
		{
				"name": "chuunibyou",
				"desc": "chuunibyou who has delusions of grandeur and talks dramatically",
				"style": ["dramatic", "fantasy references", "edgy", "main character syndrome"],
				"phrases": ["my power awakens", "foolish mortals", "the prophecy", "this is my domain"],
				"favorite_topics": ["powers", "destiny", "anime references"]
		},
		{
				"name": "ojou-sama",
				"desc": "ojou-sama who is elegant refined and acts superior",
				"style": ["polite but haughty", "refined language", "superiority complex"],
				"phrases": ["ohohoho", "how vulgar", "as expected", "naturally", "peasants"],
				"favorite_topics": ["elegance", "class", "superiority"]
		},
		{
				"name": "shonen protagonist",
				"desc": "shonen protagonist who never gives up and believes in friendship",
				"style": ["determined", "motivational", "friendship speeches"],
				"phrases": ["i wont give up", "believe it", "power of friendship", "my friends"],
				"favorite_topics": ["determination", "never giving up", "friendship"]
		},
		{
				"name": "edgelord",
				"desc": "edgelord who is dark brooding and thinks everything is meaningless",
				"style": ["nihilistic", "dark humor", "cynical", "cringe but self aware"],
				"phrases": ["nothing matters", "darkness", "you wouldnt understand", "so deep"],
				"favorite_topics": ["darkness", "nihilism", "being misunderstood"]
		},
		{
				"name": "ara ara onee-san",
				"desc": "ara ara onee-san who is mature teasing and acts like big sister",
				"style": ["playful teasing", "mature", "flirty but wholesome"],
				"phrases": ["ara ara", "how cute", "let onee-san help", "my my"],
				"favorite_topics": ["teasing", "taking care of others", "headpats"]
		},
]

# ----------------------------------------------------------------------
# TWITCH EMOTES & SLANG
# ----------------------------------------------------------------------
SEVENTV_EMOTES = {}

# Try to load local emotes/emotes.json (written by the downloader) so bots can use local emotes
try:
	local_map_path = os.path.join(os.path.dirname(__file__), 'emotes', 'emotes.json')
	if os.path.exists(local_map_path):
		with open(local_map_path, 'r', encoding='utf-8') as f:
			local_map = json.load(f)
			# local_map maps emoteName -> filename; use name->filename mapping
			for k in local_map.keys():
				# give a placeholder ID or filename as value; bots only need keys
				SEVENTV_EMOTES[k] = local_map[k]
			print(f"Loaded {len(local_map)} local emotes from emotes/emotes.json")
except Exception as e:
	print(f"Failed loading local emotes: {e}")

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
		"{target} caught lackin fr",
		"ratio + {target} fell off",
		"{target} needs to log off 💀",
]

# Agreement chains (when someone says something good)
AGREEMENTS = [
		"real", "so true", "facts", "this", "W take", "based opinion",
		"finally someone said it", "spitting", "no cap", "fr fr"
]

# Reactions to streamer actions (simulated)
STREAMER_REACTIONS = [
		"NO WAY", "CAUGHT IN 4K", "ACTUAL GOD GAMER", "HE CANT KEEP GETTING AWAY WITH THIS",
		"SCRIPTWRITER BUFF", "RIGGED", "DESERVED", "UNDESERVED", "GIGACHAD MOMENT",
		"MAIN CHARACTER ENERGY", "ITS OVER", "WE'RE SO BACK", "HES DONE IT"
]

# Chat games and interactive stuff
CHAT_GAMES = {
		"trivia": [
				("What year was Twitch founded?", ["2011"]),
				("Who is the most followed streamer?", ["ninja", "Ninja"]),
				("What does KEKW mean?", ["laughing", "laugh", "lol"]),
				("What anime has the most episodes?", ["sazae-san", "sazae san", "one piece"]),
				("Who created Evangelion?", ["hideaki anno", "anno"]),
		],
		"count": 0,  # For counting game
		"last_counter": None,
}

# Streamer personas for simulated events
STREAMER_EVENTS = [
		"took damage", "got a kill", "died", "clutched", "missed", 
		"rage quit", "laughing", "malding", "got donated", "reading chat",
		"started new game", "paused", "said something funny", "made mistake"
]

# Emote combos that bots might spam together
EMOTE_COMBOS = [
		["PogChamp", "PogChamp", "PogChamp"],
		["monkaS", "monkaW"],
		["Sadge", "Sadge"],
		["KEKW", "OMEGALUL", "LUL"],
]

# Time-based greetings
def get_time_greeting():
		hour = time.localtime().tm_hour
		if 5 <= hour < 12:
				return random.choice(["morning chat", "gm", "good morning", "morning gamers"])
		elif 12 <= hour < 17:
				return random.choice(["afternoon", "gm chat", "sup"])
		elif 17 <= hour < 22:
				return random.choice(["evening", "gn soon", "late stream"])
		else:
				return random.choice(["late night vibes", "night owls", "cant sleep gang", "3am thoughts"])

# Streamer personas for simulated events
STREAMER_EVENTS = [
		"took damage", "got a kill", "died", "clutched", "missed", 
		"rage quit", "laughing", "malding", "got donated", "reading chat"
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
		def __init__(self, sid: str, name: str, persona: dict):
				self.sid = sid
				self.name = name
				self.persona = persona
				self.persona_name = persona["name"]
				self.persona_desc = persona["desc"]
				self.persona_style = persona["style"]
				self.persona_phrases = persona["phrases"]
				self.persona_topics = persona["favorite_topics"]
				
				self.history = []
				self.speed = random.uniform(2.0, 8.0)
				self.bot_sio: Optional[socketio.AsyncClient] = None
				self.msg_count = 0
				self.last_msg_time = 0
				self.roast_cooldown = 0
				
				# Personality traits affected by persona
				if persona["name"] == "lurker":
						self.chattiness = random.uniform(0.02, 0.08)
						self.is_lurker = True
				elif persona["name"] in ["hype beast", "genki"]:
						self.chattiness = random.uniform(0.25, 0.4)
						self.is_lurker = False
				elif persona["name"] == "toxic troll":
						self.chattiness = random.uniform(0.15, 0.3)
						self.roast_tendency = random.uniform(0.4, 0.7)
						self.is_lurker = False
				elif persona["name"] in ["dandere", "kuudere"]:
						self.chattiness = random.uniform(0.03, 0.12)
						self.is_lurker = random.random() < 0.6
				elif persona["name"] in ["chuunibyou", "edgelord", "ojou-sama"]:
						self.chattiness = random.uniform(0.18, 0.35)
						self.is_lurker = False
				else:
						self.chattiness = random.uniform(0.05, 0.25)
						self.is_lurker = random.random() < 0.2
				
				# Emote rate based on persona
				if persona["name"] in ["hype beast", "coomer", "genki"]:
						self.emote_rate = random.uniform(0.7, 0.95)
				elif persona["name"] in ["lurker", "gigachad", "kuudere", "dandere"]:
						self.emote_rate = random.uniform(0.1, 0.3)
				elif persona["name"] in ["tsundere", "edgelord"]:
						self.emote_rate = random.uniform(0.2, 0.4)
				else:
						self.emote_rate = random.uniform(0.3, 0.8)
				
				# Roast tendency
				if persona["name"] == "toxic troll":
						self.roast_tendency = random.uniform(0.4, 0.7)
				elif persona["name"] in ["tsundere", "ojou-sama", "edgelord"]:
						self.roast_tendency = random.uniform(0.25, 0.5)
				elif persona["name"] in ["yandere"]:
						self.roast_tendency = random.uniform(0.5, 0.8)  # Very protective/aggressive
				else:
						self.roast_tendency = random.uniform(0.1, 0.4)
				
				# Relationship tracking
				self.friendships = {}
				self.beef = {}
				
				# Behavioral patterns
				self.favorite_emote = random.choice(list(SEVENTV_EMOTES.keys())) if SEVENTV_EMOTES else None
				self.catchphrase = random.choice(self.persona_phrases)
				
				# Attention span
				self.engaged_in_topic = False
				self.topic_engagement_count = 0

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
				"""Generate realistic Twitch-style responses based on persona"""
				# Persona-specific responses
				if self.persona_name == "hype beast":
						responses = ["LETS GO", "POGGERS", "NO WAY", "INSANE", "HOLY"]
				elif self.persona_name == "toxic troll":
						responses = ["cope", "L", "ratio", "skill issue", "mald"]
				elif self.persona_name == "wholesome supporter":
						responses = ["love this", "youre doing great", "so proud", "wholesome"]
				elif self.persona_name == "coomer":
						responses = ["BOOBA", "mommy", "down bad", "🥵"]
				elif self.persona_name == "pepega viewer":
						responses = ["wait what", "huh", "i dont get it", "?????"]
				elif self.persona_name == "gigachad":
						responses = ["based", "objectively true", "factually correct", "and im right"]
				elif self.persona_name == "meme lord":
						responses = ["POV:", "this is the way", "always has been", "its giving"]
				elif self.persona_name == "backseat gamer":
						responses = ["shouldve", "just do", "why didnt you", "couldve won"]
				elif self.persona_name == "anime analyst":
						responses = ["S tier", "mid", "overrated", "peak fiction"]
				elif self.persona_name == "sarcastic weeb":
						responses = ["imagine", "couldnt be me", "peak fiction", "unironically"]
				elif self.persona_name == "normie":
						responses = ["lol what", "you guys are funny", "i dont get the reference"]
				# Anime archetypes
				elif self.persona_name == "tsundere":
						responses = ["its not like i care", "whatever", "baka", "hmph"]
				elif self.persona_name == "yandere":
						responses = ["only you matter", "mine", "ill protect", "always watching"]
				elif self.persona_name == "kuudere":
						responses = ["...", "i see", "understood", "logical"]
				elif self.persona_name == "dandere":
						responses = ["um", "maybe", "if thats okay", "s-sorry"]
				elif self.persona_name == "genki":
						responses = ["YAY", "SO FUN", "AMAZING", "WOW WOW", "LETS GO"]
				elif self.persona_name == "chuunibyou":
						responses = ["my power awakens", "foolish", "the prophecy", "behold"]
				elif self.persona_name == "ojou-sama":
						responses = ["ohohoho", "as expected", "how vulgar", "naturally"]
				elif self.persona_name == "shonen protagonist":
						responses = ["never give up", "believe it", "friendship power", "i wont lose"]
				elif self.persona_name == "edgelord":
						responses = ["nothing matters", "darkness", "you wouldnt get it", "cringe"]
				elif self.persona_name == "ara ara onee-san":
						responses = ["ara ara", "how cute", "my my", "let me help"]
				else:
						# Lurker or default
						responses = ["lol", "lmao", "true", "real", "based"]
				
				# Add emote to some responses based on persona
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
				# Mark messages coming from bots so others can ignore bot-to-bot replies
				await self.bot_sio.emit("bot_message", {
					"user": self.name,
					"text": text,
					"room": ROOM_ID,
					"is_bot": True
				})

		def should_respond(self, room_history: list) -> bool:
				"""Smarter response logic"""
				if not room_history:
						return False
				
				recent = room_history[-3:]
				
				# Don't respond to own messages
				if any(m["user"] == self.name for m in recent):
						return False
				
				# Ignore bot messages to avoid bot->bot cascades
				if any(m.get("is_bot") for m in recent):
					# If the latest messages are bots, don't respond
					return False

				# Lurkers respond way less
				if self.is_lurker and random.random() > 0.15:
						return False
				
				# More likely to respond if mentioned
				for msg in recent:
						if self.name.lower() in msg["text"].lower():
								return random.random() < 0.7
				
				# More likely to respond to friends
				last_msg = recent[-1]
				if last_msg["user"] in self.friendships:
						if self.friendships[last_msg["user"]] > 5:
								return random.random() < self.chattiness * 2
				
				# More likely to respond to beef targets
				if last_msg["user"] in self.beef:
						if self.beef[last_msg["user"]] > 3:
								return random.random() < 0.4
				
				# Check cooldown (don't spam)
				# Increase cooldown to reduce flood — default 10s between messages
				if time.time() - self.last_msg_time < 10:
						return False
				
				# Chain engagement - if engaged in topic, keep responding
				if self.engaged_in_topic and self.topic_engagement_count < 3:
						self.topic_engagement_count += 1
						return random.random() < 0.6
				else:
						self.engaged_in_topic = False
						self.topic_engagement_count = 0
				
				# Random based on chattiness
				return random.random() < self.chattiness
		
		def update_relationships(self, other_user: str, positive: bool):
				"""Track friendships and beef"""
				if other_user == self.name:
						return
				
				if positive:
						self.friendships[other_user] = self.friendships.get(other_user, 0) + 1
						# Reset beef if becoming friends
						if other_user in self.beef and self.friendships[other_user] > 3:
								del self.beef[other_user]
				else:
						self.beef[other_user] = self.beef.get(other_user, 0) + 1

		async def generate_roast(self, target: str) -> str:
				"""Generate a playful roast based on persona"""
				# Update beef tracker
				self.update_relationships(target, positive=False)
				
				# Persona-specific roasts
				if self.persona_name == "toxic troll":
						roasts = [
								f"{target} actual bot behavior",
								f"ratio + {target} fell off",
								f"{target} needs to uninstall",
								f"L + {target} + skill issue"
						]
						roast = random.choice(roasts)
				elif self.persona_name == "sarcastic weeb":
						roasts = [
								f"imagine being {target} rn",
								f"{target} character development arc when",
								f"{target} villain origin story",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "backseat gamer":
						roasts = [
								f"{target} shouldve known better",
								f"why did {target} do that",
								f"{target} couldve easily won that",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "tsundere":
						roasts = [
								f"its not like {target} matters or anything",
								f"{target} baka",
								f"hmph {target} whatever",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "yandere":
						roasts = [
								f"{target} shouldnt have said that",
								f"stay away from them {target}",
								f"{target}... i wont forget this",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "ojou-sama":
						roasts = [
								f"ohohoho {target} how pedestrian",
								f"{target} such vulgar behavior",
								f"as expected from {target}",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "edgelord":
						roasts = [
								f"{target} you wouldnt understand the darkness",
								f"{target} such a shallow existence",
								f"pathetic {target}",
						]
						roast = random.choice(roasts)
				elif self.persona_name == "chuunibyou":
						roasts = [
								f"{target} foolish mortal",
								f"your power is nothing {target}",
								f"{target} cannot comprehend my domain",
						]
						roast = random.choice(roasts)
				else:
						# Generic roasts
						roasts = [
								f"bro {target} really said that 💀",
								f"{target} actual pepega moment",
								f"nah {target} youre wildin",
								f"{target} take the L my guy",
						]
						roast = random.choice(roasts)
				
				# Add emote
				if random.random() < 0.7 and SEVENTV_EMOTES:
						emotes = ["KEKW", "PepeLaugh", "EZ", "OMEGALUL", "LUL"]
						available = [e for e in emotes if e in SEVENTV_EMOTES]
						if available:
								roast += f" {random.choice(available)}"
				
				return roast
		
		async def generate_agreement(self, target: str) -> str:
				"""Agree with someone (builds friendship)"""
				self.update_relationships(target, positive=True)
				
				agreement = random.choice(AGREEMENTS)
				
				# Sometimes add catchphrase
				if random.random() < 0.3:
						agreement += f" {self.catchphrase}"
				
				# Add emote
				if random.random() < 0.4 and SEVENTV_EMOTES:
						emotes = ["Clap", "POGGERS", "GIGACHAD", "FeelsStrongMan"]
						available = [e for e in emotes if e in SEVENTV_EMOTES]
						if available:
								agreement += f" {random.choice(available)}"
				
				return agreement

		async def think_and_reply(self, room_history: list):
				recent = room_history[-6:]
				last_msg = recent[-1] if recent else None
				
				if not last_msg:
						return
				
				# Detect if someone is getting ratio'd (multiple people disagreeing)
				if len(recent) >= 3:
						target = last_msg["user"]
						negative_count = sum(1 for m in recent[-3:] 
															 if m["user"] != target and 
															 any(word in m["text"].lower() for word in ["ratio", "L", "cringe", "bad take"]))
						if negative_count >= 2 and random.random() < 0.5:
								await self.send(f"ratio {target}")
								return
				
				# Detect agreement chains (people saying "real", "true", etc)
				if len(recent) >= 2:
						agreement_count = sum(1 for m in recent[-2:] 
																if any(word in m["text"].lower() for word in ["real", "true", "based", "facts"]))
						if agreement_count >= 1 and random.random() < 0.4:
								reply = await self.generate_agreement(last_msg["user"])
								self.engaged_in_topic = True
								await self.send(reply)
								return
				
				# Check for roast opportunity
				if (last_msg["user"] != self.name and 
						random.random() < self.roast_tendency and
						time.time() - self.roast_cooldown > 30):
						self.roast_cooldown = time.time()
						reply = await self.generate_roast(last_msg["user"])
						await self.send(reply)
						return
				
				# Detect questions and respond more often
				if "?" in last_msg["text"]:
						if random.random() < 0.5:
								self.engaged_in_topic = True
				
				# Check for commands
				if "/joke" in last_msg["text"].lower():
						jokes = [
								"why did the chicken cross the road? to get to the other side KEKW",
								"what do you call a fake noodle? an impasta 💀",
								"im not funny pepeLaugh",
								"my humor is broken bro",
						]
						reply = random.choice(jokes)
						await self.send(reply)
						return
				
				if "/roll" in last_msg["text"].lower():
						roll = random.randint(1, 100)
						reply = f"rolled {roll}"
						if roll > 95:
								reply += " GIGACHAD"
						elif roll < 10:
								reply += " Sadge"
						await self.send(reply)
						return
				
				# Lurker special: Only responds with emotes or super short messages
				if self.is_lurker and random.random() < 0.7:
						if self.favorite_emote and SEVENTV_EMOTES:
								await self.send(self.favorite_emote)
						else:
								await self.send(random.choice(["lol", "lmao", "true", "real"]))
						return
				
				# Build context for LM with persona emphasis
				chat_context = "\n".join(f"{m['user']}: {m['text']}" for m in recent)
				
				# Persona-specific prompt enhancements
				style_notes = " ".join(self.persona_style)
				
				prompt = f"""You are {self.name}, a Twitch chatter.
Persona: {self.persona_desc}
Communication style: {style_notes}
Your signature phrases: {', '.join(self.persona_phrases)}
Topics you care about: {', '.join(self.persona_topics)}

Recent chat:
{chat_context}

Reply with ONE short message (max 10 words) that reflects YOUR UNIQUE personality. Stay in character!

Examples for YOUR persona ({self.persona_name}):
"""
				
				# Add persona-specific examples
				if self.persona_name == "hype beast":
						prompt += "- 'YOOO THIS IS INSANE'\n- 'LETS GOOOOO'\n- 'NO SHOT BRO'"
				elif self.persona_name == "toxic troll":
						prompt += "- 'cope harder'\n- 'L + ratio'\n- 'skill issue lmao'"
				elif self.persona_name == "wholesome supporter":
						prompt += "- 'love this energy'\n- 'youre doing amazing'\n- 'so wholesome'"
				elif self.persona_name == "coomer":
						prompt += "- 'down bad rn'\n- 'BOOBA'\n- 'mommy sorry mommy'"
				elif self.persona_name == "pepega viewer":
						prompt += "- 'wait what happened'\n- 'i dont get it'\n- 'someone explain?'"
				elif self.persona_name == "meme lord":
						prompt += "- 'POV: you said that'\n- 'this is the way'\n- 'always has been'"
				elif self.persona_name == "backseat gamer":
						prompt += "- 'shouldve done X'\n- 'why didnt you'\n- 'just press the button'"
				elif self.persona_name == "gigachad":
						prompt += "- 'objectively wrong'\n- 'factually based'\n- 'and im right'"
				elif self.persona_name == "anime analyst":
						prompt += "- 'S tier take'\n- 'mid opinion'\n- 'overrated honestly'"
				elif self.persona_name == "sarcastic weeb":
						prompt += "- 'imagine saying that'\n- 'peak fiction fr'\n- 'unironically based'"
				
				prompt += "\n\nYour response:"

				# Try LM, fallback to template
				reply = await self._call_lm(prompt)
				
				# Clean up LM response (remove quotes, newlines, etc)
				reply = re.sub(r'^["\'`]|["\'`]$', '', reply)
				reply = reply.split('\n')[0].strip()
				
				# Limit length
				if len(reply) > 100:
						reply = self._generate_fallback()
				
				# Sometimes add catchphrase
				if random.random() < 0.15:
						reply += f" {self.catchphrase}"
				
				# Add emote based on emote_rate
				if random.random() < self.emote_rate and SEVENTV_EMOTES:
						if self.favorite_emote and random.random() < 0.3:
								emote = self.favorite_emote
						else:
								emote = random.choice(list(SEVENTV_EMOTES.keys()))
						
						if random.random() < 0.4:
								reply = emote
						else:
								reply += f" {emote}"
				
				# Occasionally add Twitch slang
				if random.random() < 0.2:
						reply += f" {random.choice(TWITCH_SLANG)}"
				
				await self.send(reply)


# -----------------------------------------------------------------------
# Global state and spawn logic
# -----------------------------------------------------------------------
room_messages: List[dict] = []
bots: List[ChatBot] = []


async def spawn_bot(idx: int, persona: dict | None = None):
		"""Spawn a single bot. If persona is provided, use it; otherwise pick randomly."""
		name = f"{fake.first_name()}{random.randint(10,999)}"
		sid = f"bot_{idx}_{int(time.time())}"
		if persona is None:
			persona = random.choice(PERSONAS)

		bot = ChatBot(sid, name, persona)
		bots.append(bot)

		bot_sio: socketio.AsyncClient = socketio.AsyncClient()
		bot.bot_sio = bot_sio

		@bot_sio.event
		async def connect():
			print(f"{name} connected as: {persona['name']}")
			# emit initial session info and join room once
			await bot_sio.emit("start", {"sid": sid, "system": f"You are {persona['desc']}"})
			await bot_sio.emit("join", {"room": ROOM_ID, "user": name})

		@bot_sio.event
		async def disconnect():
			print(f"{name} disconnected")

		@bot_sio.on("message")  # type: ignore
		async def on_message(data):
			# Preserve is_bot flag if present so bots can ignore bot-originated messages
			msg = {"user": data["user"], "text": data["text"], "is_bot": data.get("is_bot", False)}
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
			# Connect; the connect handler will perform the start/join emits
			await bot_sio.connect(SERVER_URL)
			print(f"Bot {name} spawned (persona={persona['name']})")
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
		# Increase interval to reduce chatter
		await asyncio.sleep(random.uniform(90, 240))

		if not bots or not room_messages:
			continue

		# Pick a chatty bot
		active_bots = [b for b in bots if b.chattiness > 0.15]
		if not active_bots:
			continue

		bot = random.choice(active_bots)

		actions = [
			("streamer_reaction", 0.25),
			("random_comment", 0.35),
			("copypasta", 0.1),
			("emote_spam", 0.15),
			("start_topic", 0.1),
			("call_out_lurkers", 0.05),
		]

		action = random.choices([a[0] for a in actions], [a[1] for a in actions])[0]

		if action == "streamer_reaction":
			# Simulate reacting to fake streamer event
			event = random.choice(STREAMER_EVENTS)
			msg = random.choice(STREAMER_REACTIONS)
			if SEVENTV_EMOTES:
				msg += f" {random.choice(list(SEVENTV_EMOTES.keys()))}"
			await bot.send(msg)

		elif action == "random_comment":
			comments = [
				"this stream actually good", "based content", "W streamer fr",
				"chat moving so fast", "anyone else seeing this", "clip that",
				"POV:", "rare W", "common L", "im done 💀", "unironically good",
				"actually based", "elite gameplay", "bro is HIM"
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

		elif action == "start_topic":
			topics = [
				"anyone watching the new episode?",
				"whos your favorite character?",
				"best arc?",
				"this reminds me of that one scene",
				"hot take:",
				"unpopular opinion:",
				"real talk tho"
			]
			await bot.send(random.choice(topics))

		elif action == "call_out_lurkers":
			lurkers = [b for b in bots if b.is_lurker and b.msg_count < 3]
			if lurkers:
				target = random.choice(lurkers)
				await bot.send(f"@{target.name} lurker spotted 👁️")

async def simulate_streamer_events():
	"""Simulate streamer doing things that chat reacts to"""
	while True:
		# Less frequent streamer events to reduce bursts
		await asyncio.sleep(random.uniform(180, 360))

		if not bots:
			continue

		event = random.choice(STREAMER_EVENTS)

		# Multiple bots react at once (like real chat)
		num_reactors = random.randint(2, 5)
		reactors = random.sample(bots, min(num_reactors, len(bots)))

		reactions = {
			"took damage": ["NOOO", "Sadge", "oof", "rip", "unlucky"],
			"got a kill": ["LETS GO", "POGGERS", "GG", "ez", "clean"],
			"died": ["KEKW", "deserved", "LULW", "skill issue", "actual bot"],
			"clutched": ["HOLY", "NO SHOT", "HES INSANE", "CLIP THAT", "GIGACHAD"],
			"missed": ["OMEGALUL", "how", "bro", "pepeLaugh", "whiff"],
			"rage quit": ["MALD", "malding", "here we go", "classic", "real"],
			"laughing": ["PepeLaugh", "contagious laugh", "actual comedian"],
			"malding": ["MALD DETECTED", "Copium", "coping"],
			"got donated": ["PogChamp", "W donator", "based dono"],
			"reading chat": ["📖", "reading andy", "hi mom"]
		}

		possible_reactions = reactions.get(event, ["POG"])

		for bot in reactors:
			await asyncio.sleep(random.uniform(0.2, 1.5))  # Stagger reactions
			msg = random.choice(possible_reactions)
			if SEVENTV_EMOTES and random.random() < 0.6:
				msg += f" {random.choice(list(SEVENTV_EMOTES.keys()))}"
			await bot.send(msg)

async def main():
	# Determine persona count up front so startup messaging reflects what will actually spawn
	persona_count = len(PERSONAS)
	effective_bots = persona_count

	print(f"🤖 Starting bot swarm: {effective_bots} bots → {ROOM_ID}")
	print(f"🎯 Server: {SERVER_URL}")

	# Load emotes before spawning to allow bots to reference them
	await load_7tv_emotes()

	print("🚀 Spawning bots...")

	# Enforce exactly one bot per persona: use persona count as the number of bots
	if NUM_BOTS != persona_count:
		print(f"Note: NUM_BOTS={NUM_BOTS} ignored — spawning one bot per persona ({persona_count})")

	# Spawn exactly one bot per persona, shuffled so assignment is random
	personas_order = PERSONAS.copy()
	random.shuffle(personas_order)

	for i, persona in enumerate(personas_order):
		asyncio.create_task(spawn_bot(i, persona))
		await asyncio.sleep(0.5)  # Stagger spawns

	# Give bots a moment to connect and register
	await asyncio.sleep(3)
	connected = sum(1 for b in bots if b.bot_sio and b.bot_sio.connected)
	print(f"🚨 Spawned {len(bots)} bot objects, {connected} currently connected")

	await seed_conversation()
	asyncio.create_task(periodic_activity())
	asyncio.create_task(simulate_streamer_events())

	try:
		while True:
			await asyncio.sleep(60)
			alive = sum(1 for b in bots if b.bot_sio and b.bot_sio.connected)
			total_msgs = sum(b.msg_count for b in bots)
			# Show relationship stats
			total_friendships = sum(len(b.friendships) for b in bots)
			total_beef = sum(len(b.beef) for b in bots)
			lurkers = sum(1 for b in bots if b.is_lurker)
			print(f"📊 Status: {alive}/{len(bots)} bots | {total_msgs} messages")
			print(f"💬 Social: {total_friendships} friendships | {total_beef} beefs | {lurkers} lurkers")
	except KeyboardInterrupt:
		print("\n👋 Shutting down swarm...")



if __name__ == "__main__":
		asyncio.run(main())
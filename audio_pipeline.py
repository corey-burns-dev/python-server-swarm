import asyncio
import io
import os
import random
import numpy as np
import pyaudio
import socketio
import wave
from typing import List
import whisper
import aiohttp
from openai import OpenAI  # For cloud fallback; optional

# Config (reuse from your swarm)
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000")
LM_API = os.getenv("LM_API", "http://localhost:1234/v1/chat/completions")
ROOM_ID = os.getenv("ROOM_ID", "test-room-123")
WHISPER_MODEL_SIZE = "base"  # "tiny" for faster, "small" for better accuracy
CHUNK_DURATION = 5  # Seconds per audio chunk
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16

# Load Whisper model (local, offline)
whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)

# Socket.IO client for swarm integration
sio = socketio.AsyncClient()

# Your personas (copied from bots.py for reaction variety)
PERSONAS = [  # ... (paste the full PERSONAS list from your bots.py here for brevity)
    {"name": "hype beast", "desc": "hype beast who gets excited about everything", ...},
    # Add all 22 as in your file
]

# Global: Track connected bots (from swarm) for random selection
connected_bots = []

async def connect_to_swarm():
    """Connect to swarm server and fetch bot list (assume swarm emits 'bot_list' on connect)."""
    global connected_bots
    @sio.event
    async def connect():
        print(f"Connected to swarm at {SERVER_URL}")
        # Join room
        await sio.emit("join", {"room": ROOM_ID, "user": "audio_pipeline"})

    @sio.event
    async def bot_list(data):
        connected_bots = data.get("bots", [])  # Assume swarm sends list of active bot names

    @sio.event
    async def disconnect():
        print("Disconnected from swarm")

    await sio.connect(SERVER_URL)
    # Emit to request bot list (add this emit to your swarm if needed)
    await sio.emit("request_bot_list", {"room": ROOM_ID})

async def send_reaction_to_chat(text: str):
    """Send reaction as a random bot in the swarm."""
    if not connected_bots:
        print(f"[CHAT] No bots available, printing reaction: {text}")
        return
    bot_name = random.choice(connected_bots)
    print(f"[{bot_name}] → {text}")
    await sio.emit("bot_message", {"user": bot_name, "text": text, "room": ROOM_ID})

async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe raw audio bytes with Whisper (local). Fallback to OpenAI API if fails."""
    try:
        # Load audio into Whisper format
        audio_np = np.frombuffer(audio_bytes, np.int16).astype(np.float32) / 32768.0
        result = whisper_model.transcribe(audio_np, fp16=False)  # CPU-friendly
        text = result["text"].strip()
        if text:
            return text
    except Exception as e:
        print(f"Local Whisper failed: {e}. Trying OpenAI API fallback...")
    
    # Fallback: OpenAI API (cloud)
    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        try:
            with io.BytesIO(audio_bytes) as audio_file:
                audio_file.name = "temp.wav"  # Whisper expects .wav
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript.text.strip()
        except Exception as e:
            print(f"Cloud Whisper failed: {e}")
    return ""

async def generate_llm_reaction(transcript: str, session: aiohttp.ClientSession) -> str:
    """Generate Twitch-style reaction via your local LLM."""
    if not transcript:
        return ""
    
    # Prompt: Twitch-aware, short reaction
    prompt = f"""You are a Twitch chat bot reacting to streamer speech: "{transcript}".

Reply with ONE short, hype/sarcastic/emote-filled message (under 20 words). Stay fun and in-character like a viewer."""

    payload = {
        "model": "gpt-4o-mini",  # Or your LM_MODEL env
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 50,
    }
    
    try:
        async with session.post(LM_API, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"].strip()
                # Clean: Remove quotes/newlines, add random emote if possible
                reply = reply.replace('\n', ' ').strip('"\'`')
                if random.random() < 0.5:
                    reply += f" {random.choice(['PogChamp', 'KEKW', 'LUL'])}"
                return reply
    except Exception as e:
        print(f"LLM reaction failed: {e}")
        # Fallback: Simple reaction
        return random.choice(["Poggers!", "No way!", "Based take.", "KEKW"])

async def audio_capture_loop():
    """Continuous mic capture in chunks."""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                    input=True, frames_per_buffer=1024)

    print("Listening for audio... (Speak now!)")
    try:
        while True:
            # Capture chunk
            frames = []
            for _ in range(0, int(SAMPLE_RATE / 1024 * CHUNK_DURATION)):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            
            # Convert to bytes
            audio_bytes = b''.join(frames)
            
            # Transcribe
            transcript = await transcribe_audio(audio_bytes)
            if transcript:
                print(f"[TRANSCRIPT] {transcript}")
                
                # LLM reaction
                async with aiohttp.ClientSession() as session:
                    reaction = await generate_llm_reaction(transcript, session)
                    if reaction:
                        await send_reaction_to_chat(reaction)
    except KeyboardInterrupt:
        print("Stopping audio capture...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

async def main():
    # Connect to swarm
    await connect_to_swarm()
    
    # Start audio loop
    await audio_capture_loop()

if __name__ == "__main__":
    asyncio.run(main())
# server.py
import os
import json
import requests
import aiohttp
import subprocess
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import defaultdict

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
LM_API = os.getenv("LM_API", "http://localhost:1234/v1/chat/completions")
MODEL = os.getenv("LM_MODEL", "lmstudio-community/Meta-Llama-3-8B-Instruct")

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
conversations = {}                    # sid → message history
online_users = defaultdict(set)       # room → set of usernames
socket_data = {}                      # sid → {room, user}

# ----------------------------------------------------------------------
# 7TV Emotes
# ----------------------------------------------------------------------
SEVENTV_EMOTES = {}  # name -> id

def load_7tv_emotes():
    global SEVENTV_EMOTES
    try:
        with open('emotes/emotes.json', 'r') as f:
            SEVENTV_EMOTES = json.load(f)
        print(f"Loaded {len(SEVENTV_EMOTES)} emotes from local file")
    except FileNotFoundError:
        print("emotes.json not found, using fallback")
        SEVENTV_EMOTES = {
            "PogChamp": "01FAGRADQ00008E6R5BC5KRVKP.webp",
            "Kappa": "01FAGRAEQ00008E6R5BC5KRVKR.webp",
            "LUL": "01FAGRADQ00008E6R5BC5KRVKR.webp",
            "OMEGALUL": "01FAGRADQ00008E6R5BC5KRVKS.webp",
            "PepeLaugh": "01FAGRADQ00008E6R5BC5KRVKT.webp",
            "monkaS": "01FAGRADQ00008E6R5BC5KRVKU.webp"
        }
    except Exception as e:
        print(f"Error loading emotes: {e}")
        SEVENTV_EMOTES = {
            "PogChamp": "01FAGRADQ00008E6R5BC5KRVKP.webp",
            "Kappa": "01FAGRAEQ00008E6R5BC5KRVKR.webp",
            "LUL": "01FAGRADQ00008E6R5BC5KRVKR.webp",
            "OMEGALUL": "01FAGRADQ00008E6R5BC5KRVKS.webp",
            "PepeLaugh": "01FAGRADQ00008E6R5BC5KRVKT.webp",
            "monkaS": "01FAGRADQ00008E6R5BC5KRVKU.webp"
        }

    # Run download-7tv.js to download emotes locally
    try:
        print("Running download-7tv.js...")
        subprocess.run(['node', 'download-7tv.js'], check=True, timeout=60)
        print("Emotes downloaded successfully")
        # Reload after download
        try:
            with open('emotes/emotes.json', 'r') as f:
                SEVENTV_EMOTES = json.load(f)
            print(f"Reloaded {len(SEVENTV_EMOTES)} emotes after download")
        except:
            pass
    except subprocess.CalledProcessError as e:
        print(f"download-7tv.js failed: {e}")
    except FileNotFoundError:
        print("download-7tv.js not found, skipping download")
    except subprocess.TimeoutExpired:
        print("download-7tv.js timed out")

# ----------------------------------------------------------------------
@socketio.on("connect")
def on_connect():
    sid = request.sid
    print(f"[CONNECT] Client {sid}")
    emit("emotes", SEVENTV_EMOTES)
    emit("status", {"message": "Connected to server."})

# ----------------------------------------------------------------------
@socketio.on("join")
def handle_join(data):
    room = data.get("room")
    user = data.get("user")
    sid = request.sid

    if not room or not user:
        emit("error", {"message": "Missing room or user"})
        return

    join_room(room)
    socket_data[sid] = {"room": room, "user": user}
    online_users[room].add(user)

    print(f"[JOIN] {user} → {room}")
    # Tell everyone a user joined
    emit("user_joined", {"user": user}, room=room)
    emit("status", {"message": f"{user} joined"}, room=room)
    # Send the current user list to the newly-joined client so they see existing users (including bots)
    try:
        emit("user_list", {"users": list(online_users[room])}, to=sid)
    except Exception:
        # fallback: emit without explicit target
        emit("user_list", {"users": list(online_users[room])})

# ----------------------------------------------------------------------
@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    data = socket_data.get(sid)
    if not data:
        return

    room = data["room"]
    user = data["user"]

    leave_room(room)
    online_users[room].discard(user)
    if not online_users[room]:
        del online_users[room]

    del socket_data[sid]
    print(f"[LEAVE] {user} left {room}")
    emit("user_left", {"user": user}, room=room)

# ----------------------------------------------------------------------
@socketio.on("start")
def on_start(data):
    sid = data.get("sid") or request.sid
    system = data.get("system", "You are a helpful assistant.")
    conversations[sid] = [{"role": "system", "content": system}]
    emit("status", {"message": "Conversation started."})

# ----------------------------------------------------------------------
@socketio.on("typing")
def handle_typing(data):
    sid = request.sid
    info = socket_data.get(sid)
    if info:
        # Broadcast to **everyone except the typer** (they already show their own)
        emit("typing", {"user": info["user"]}, room=info["room"], include_self=False)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    sid = request.sid
    info = socket_data.get(sid)
    if info:
        emit("stop_typing", {"user": info["user"]}, room=info["room"], include_self=False)

# ----------------------------------------------------------------------
@socketio.on("message")
def on_message(data):
    sid = request.sid
    user_text = data.get("text", "").strip()
    room = data.get("room")
    user = data.get("user")

    # Validate session
    info = socket_data.get(sid)
    if not info or info["room"] != room or info["user"] != user:
        emit("error", {"message": "Invalid session"}, to=sid)
        return
    if not user_text:
        return

    # Check for AI trigger
    ai_trigger = False  # AI muted - only bots chat

    if not ai_trigger:
        # Don't respond
        return

    # Append user message
    messages = conversations.setdefault(sid, [{"role": "system", "content": "You are a helpful assistant."}])
    messages.append({"role": "user", "content": user_text})

    # Call LM with streaming
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "stream": True
    }

    try:
        with requests.post(LM_API, json=payload, stream=True) as r:
            r.raise_for_status()
            full_reply = []

            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                if line.strip() == "data: [DONE]":
                    break
                try:
                    chunk = json.loads(line[len("data:"):].strip())
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        full_reply.append(delta)
                        # STREAM TO **EVERYONE IN THE ROOM** (not just sender)
                        emit("stream", {"token": delta}, room=room)
                except Exception as e:
                    print(f"Stream parse error: {e}")

            reply_text = "".join(full_reply).strip()
            if not reply_text:
                reply_text = "(no response)"

            messages.append({"role": "assistant", "content": reply_text})

            # Signal end of streaming
            emit("done", room=room)

            # BROADCAST FINAL MESSAGE TO WHOLE ROOM
            emit("message", {"user": "AI Assistant", "text": reply_text}, room=room)

    except requests.RequestException as e:
        error_msg = f"LM request failed: {e}"
        print(error_msg)
        emit("error", {"message": error_msg}, to=sid)

# ----------------------------------------------------------------------
@socketio.on("bot_message")
def on_bot_message(data):
    user = data.get("user")
    text = data.get("text", "").strip()
    room = data.get("room")

    if not user or not text or not room:
        return

    # Broadcast to room without calling LM
    emit("message", {"user": user, "text": text}, room=room)

# ----------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# ----------------------------------------------------------------------
# Emote serving
# ----------------------------------------------------------------------
@app.route('/emotes/<path:filename>')
def serve_emote(filename):
    return send_from_directory('emotes', filename)

# ----------------------------------------------------------------------
@app.route('/socket.io.js')
def serve_socketio():
    response = send_from_directory('static', 'socket.io.min.js')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# ----------------------------------------------------------------------
if __name__ == "__main__":
    load_7tv_emotes()
    print("Starting Flask-SocketIO server on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
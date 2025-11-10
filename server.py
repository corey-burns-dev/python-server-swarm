# server.py
import os
import json
import requests
from flask import Flask, request
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
@socketio.on("connect")
def on_connect():
    sid = request.sid
    print(f"[CONNECT] Client {sid}")
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
    emit("user_joined", {"user": user}, room=room)
    emit("status", {"message": f"{user} joined"}, room=room)

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
        emit("typing", {"user": info["user"]}, room=info["room"], include_self=False)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    sid = request.sid
    info = socket_data.get(sid)
    if info:
        emit("stop_typing", {"user": info["user"]}, room=info["room"], include_self=False)

# ----------------------------------------------------------------------
# HUMAN MESSAGES → LM + STREAM TO ALL
# ----------------------------------------------------------------------
@socketio.on("message")
def on_human_message(data):
    sid = request.sid
    user_text = data.get("text", "").strip()
    room = data.get("room")
    user = data.get("user")

    info = socket_data.get(sid)
    if not info or info["room"] != room or info["user"] != user or not user_text:
        emit("error", {"message": "Invalid session"}, to=sid)
        return

    # Append to history
    messages = conversations.setdefault(sid, [{"role": "system", "content": "You are a helpful assistant."}])
    messages.append({"role": "user", "content": user_text})

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
                        emit("stream", {"token": delta}, room=room)
                except Exception as e:
                    print(f"Stream parse error: {e}")

            reply_text = "".join(full_reply).strip() or "(no response)"
            messages.append({"role": "assistant", "content": reply_text})

            emit("done", room=room)
            emit("message", {"user": "AI Assistant", "text": reply_text}, room=room)

    except requests.RequestException as e:
        error_msg = f"LM failed: {e}"
        print(error_msg)
        emit("error", {"message": error_msg}, to=sid)

# ----------------------------------------------------------------------
# BOT MESSAGES → JUST BROADCAST (NO LM)
# ----------------------------------------------------------------------
@socketio.on("bot_message")
def on_bot_message(data):
    user = data.get("user")
    text = data.get("text", "").strip()
    room = data.get("room")

    if not user or not text or not room:
        return

    print(f"[BOT] {user}: {text}")
    emit("message", {"user": user, "text": text}, room=room)

# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting Flask-SocketIO server on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
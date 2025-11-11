from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import json
import os
import time
import random

app = Flask(__name__)
CORS(app, origins="*")

# Use threading for Python 3.13 compatibility
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
rooms = {}  # room_id -> {users: set(), messages: list()}
user_sessions = {}  # sid -> {user: str, room: str, last_seen: float}
EMOTE_MAP = {}

# Load emote map if available
try:
    emotes_path = os.path.join(os.path.dirname(__file__), 'emotes', 'emotes.json')
    if os.path.exists(emotes_path):
        with open(emotes_path, 'r', encoding='utf-8') as f:
            EMOTE_MAP = json.load(f)
            print(f"Loaded {len(EMOTE_MAP)} emotes from emotes/emotes.json")
    else:
        print("No emotes/emotes.json found; clients will receive empty emote map")
except Exception as e:
    print(f"Error loading emote map: {e}")

@app.route('/')
def index():
    # Prefer templates/index.html when present (Flask templates directory);
    # if not, serve the project's root `index.html` directly so the static
    # single-file client works when run from source.
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(templates_dir):
        return render_template('index.html')
    root = os.path.dirname(__file__)
    return send_from_directory(root, 'index.html')


# Serve emote image files from the emotes directory
@app.route('/emotes/<path:filename>')
def emote_file(filename):
    emotes_dir = os.path.join(os.path.dirname(__file__), 'emotes')
    return send_from_directory(emotes_dir, filename)


# Provide the emote mapping as JSON at a stable URL for debugging
@app.route('/emotes.json')
def emote_map():
    # Debug: log request info to help diagnose external 404s
    try:
        print('emote_map request:', request.method, request.path, dict(request.headers))
    except Exception:
        pass
    return jsonify(EMOTE_MAP)

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")
    user_sessions[request.sid] = {
        'user': None,
        'room': None,
        'last_seen': time.time()
    }
    # Send emote mapping to client so it can render emotes
    try:
        emit('emotes', EMOTE_MAP)
    except Exception:
        # emit may not be available in some contexts; ignore failures
        pass

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    session = user_sessions.get(request.sid)
    if session and session['room'] and session['user']:
        room_id = session['room']
        user = session['user']
        if room_id in rooms and user in rooms[room_id]['users']:
            rooms[room_id]['users'].remove(user)
            emit('user_left', {'user': user}, room=room_id)
            print(f"User {user} left room {room_id}")
    if request.sid in user_sessions:
        del user_sessions[request.sid]

@socketio.on('start')
def handle_start(data):
    """Initialize session"""
    sid = data.get('sid')
    system = data.get('system', '')
    user_sessions[request.sid]['system'] = system
    print(f"Session started for {request.sid}: {system}")

@socketio.on('join')
def handle_join(data):
    room_id = data.get('room')
    user = data.get('user')

    if not room_id or not user:
        emit('error', {'message': 'Room and user required'})
        return

    # Leave current room if any
    session = user_sessions.get(request.sid)
    if session and session['room']:
        old_room = session['room']
        if old_room in rooms and session['user'] in rooms[old_room]['users']:
            rooms[old_room]['users'].remove(session['user'])
            emit('user_left', {'user': session['user']}, room=old_room)

    # Join new room
    join_room(room_id)
    session = user_sessions[request.sid]
    session['user'] = user
    session['room'] = room_id
    session['last_seen'] = time.time()

    # Initialize room if needed
    if room_id not in rooms:
        rooms[room_id] = {'users': set(), 'messages': []}

    rooms[room_id]['users'].add(user)

    # Send room history
    emit('room_history', {
        'messages': rooms[room_id]['messages'][-50:],  # Last 50 messages
        'users': list(rooms[room_id]['users'])
    })

    # Ensure the joining client receives the emote mapping (avoid connect-time races)
    try:
        emit('emotes', EMOTE_MAP, room=request.sid)
    except Exception:
        pass

    # Notify others
    emit('user_joined', {'user': user}, room=room_id, skip_sid=request.sid)
    emit('joined', {'room': room_id, 'user': user})

    print(f"User {user} joined room {room_id}")

@socketio.on('leave')
def handle_leave():
    session = user_sessions.get(request.sid)
    if session and session['room'] and session['user']:
        room_id = session['room']
        user = session['user']
        leave_room(room_id)
        if room_id in rooms and user in rooms[room_id]['users']:
            rooms[room_id]['users'].remove(user)
            emit('user_left', {'user': user}, room=room_id)
        session['room'] = None
        emit('left')

@socketio.on('message')
def handle_message(data):
    user = data.get('user')
    text = data.get('text')
    room_id = data.get('room')

    if not user or not text or not room_id:
        emit('error', {'message': 'User, text, and room required'})
        return

    # Update session
    session = user_sessions.get(request.sid)
    if session:
        session['last_seen'] = time.time()

    # Create message
    message = {
        'user': user,
        'text': text,
        'timestamp': time.time(),
        'id': f"{user}_{int(time.time() * 1000)}"
    }

    # Store in room history
    if room_id in rooms:
        rooms[room_id]['messages'].append(message)
        # Keep only last 200 messages
        if len(rooms[room_id]['messages']) > 200:
            rooms[room_id]['messages'] = rooms[room_id]['messages'][-200:]

    # Broadcast to room
    emit('message', message, room=room_id)
    print(f"Message from {user} in {room_id}: {text}")

@socketio.on('bot_message')
def handle_bot_message(data):
    """Handle messages from bots"""
    user = data.get('user')
    text = data.get('text')
    room_id = data.get('room')

    if not user or not text or not room_id:
        return

    # Create message
    message = {
        'user': user,
        'text': text,
        'timestamp': time.time(),
        'id': f"bot_{user}_{int(time.time() * 1000)}",
        'is_bot': True
    }

    # Store in room history
    if room_id in rooms:
        rooms[room_id]['messages'].append(message)
        if len(rooms[room_id]['messages']) > 200:
            rooms[room_id]['messages'] = rooms[room_id]['messages'][-200:]

    # Broadcast to room
    emit('message', message, room=room_id)
    print(f"Bot message from {user} in {room_id}: {text}")

@socketio.on('typing')
def handle_typing(data):
    room_id = data.get('room')
    user = data.get('user')
    if room_id and user:
        emit('typing', {'user': user}, room=room_id, skip_sid=request.sid)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    room_id = data.get('room')
    user = data.get('user')
    if room_id and user:
        emit('stop_typing', {'user': user}, room=room_id, skip_sid=request.sid)

@socketio.on('ping')
def handle_ping():
    """Keep-alive ping"""
    session = user_sessions.get(request.sid)
    if session:
        session['last_seen'] = time.time()
    emit('pong')

# Health check endpoint
@app.route('/health')
def health():
    return {'status': 'healthy', 'rooms': len(rooms), 'sessions': len(user_sessions)}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
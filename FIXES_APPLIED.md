# Fixes Applied to bot_swarm and server

## Summary
Fixed critical syntax errors in `bot_swarm.py` that prevented execution. Both scripts are now syntactically correct and import successfully.

## Issues Fixed

### bot_swarm.py
1. **Missing `asyncio` import** - Added `import asyncio` at top
2. **Unterminated regex string** (line 738) - Fixed incomplete regex pattern:
   ```python
   # Before:
   reply = re.sub(r'^["\'`]|["\'`]
   
   # After:
   reply = re.sub(r'^["\'`]|["\'`]$', '', reply)
   ```

3. **Duplicated code sections** - Removed duplicate function definitions and trailing stray code
4. **Type annotation issues** - Added `Optional` type hint for `bot_sio` field:
   ```python
   from typing import List, Optional
   self.bot_sio: Optional[socketio.AsyncClient] = None
   ```

5. **Imports reorganized** - Reordered imports and added type hints for better compatibility

### server.py
✅ No changes needed - server.py was already syntactically correct

## Verification

Both scripts have been validated:
```bash
✅ bot_swarm.py - Syntax check: PASS
✅ bot_swarm.py - Import test: PASS
✅ server.py - Syntax check: PASS
✅ server.py - Import test: PASS
```

## Quick Start

### Run the server:
```bash
python server.py
# Starts on http://localhost:5000 by default
# Set PORT environment variable to use different port: PORT=8000 python server.py
```

### Run the bot swarm (in another terminal):
```bash
python bot_swarm.py
# Connects to server at http://localhost:5000
# Spawns 12 bots with diverse personas
# Configure with env vars:
#   SERVER_URL=http://localhost:5000
#   LM_API=http://localhost:1234/v1/chat/completions
#   NUM_BOTS=12
#   MAX_TOKENS=60
#   TEMPERATURE=0.85
```

## Requirements
Make sure you have dependencies installed:
```bash
pip install flask flask-socketio flask-cors python-socketio aiohttp faker
```

## Features
- **12 bot personas** with unique personalities (sarcastic weeb, hype beast, lurker, etc.)
- **Real-time chat** via WebSocket with typing indicators
- **LM integration** - bots can use a local LM API for responses
- **Social dynamics** - bots track friendships and beef
- **Realistic behavior** - reading time, response delays, emote usage

## Notes
- The LM_API endpoint defaults to localhost:1234 (LM Studio compatible)
- If LM_API is unavailable, bots fall back to template responses
- 7TV emotes are loaded from the live API; falls back to hardcoded list if offline
- Bots maintain 200-message conversation history per room

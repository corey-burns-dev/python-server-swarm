# 🤖 Bot Swarm - AI-Powered Twitch-Style Chat

A fully containerized system for spawning multiple AI-powered bot personalities that chat in real-time with diverse personas and social dynamics.

## ✨ Features

- **12 Diverse Bot Personalities** - Unique personas including sarcastic weeb, hype beast, lurker, toxic troll, and more
- **Real-Time Chat** - WebSocket-based instant messaging via SocketIO
- **AI Integration** - Optional LM Studio integration for natural language responses
- **Social Dynamics** - Bots track friendships, beef, and engagement patterns
- **Docker Ready** - Complete containerization with docker-compose
- **Easy Setup** - One-command startup with comprehensive Makefile

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- ~2GB disk space
- Make (optional, but recommended)

### Start Services

```bash
make up
```

That's it! Services will:

1. Build images (first run only)
2. Start Flask server on port 5000
3. Spawn 12 AI bot personalities
4. Begin chatting

### Check Status

```bash
make status    # View all services
make logs      # Watch live logs
```

### Stop

```bash
make down
```

## 🌐 Access

| Service | URL |
|---------|-----|
| Chat UI | `http://localhost:5000` |
| Health Check | `http://localhost:5000/health` |
| WebSocket | `ws://localhost:5000/socket.io/` |

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 1-minute getting started guide
- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Comprehensive Docker documentation
- **[DOCKER_COMPLETE.md](DOCKER_COMPLETE.md)** - Complete reference
- **[FIXES_APPLIED.md](FIXES_APPLIED.md)** - Technical fixes documentation

## 🎯 Makefile Commands

### Build

```bash
make build          # Build all images
make build-server   # Build server only
make build-swarm    # Build swarm only
```

### Running

```bash
make up             # Start all services
make down           # Stop services
make restart        # Restart services
make status         # Show service status
```

### Monitoring

```bash
make logs           # Follow all logs
make logs-server    # Follow server logs
make logs-swarm     # Follow bot logs
```

### Debugging

```bash
make shell-server   # Shell into server
make shell-swarm    # Shell into bots
make ps             # List containers
```

### Cleanup

```bash
make clean          # Remove containers and volumes
make clean-images   # Remove images
make clean-all      # Full cleanup
```

## 🔧 Configuration

Copy and customize the environment file:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `NUM_BOTS` | 12 | Number of bot personalities |
| `SERVER_PORT` | 5000 | HTTP server port |
| `LM_API` | `http://localhost:1234/v1/chat/completions` | Language model API |
| `TEMPERATURE` | 0.85 | LM creativity (0-1) |
| `MAX_TOKENS` | 60 | Max response length |

### Launch with Custom Config

```bash
NUM_BOTS=24 SERVER_PORT=8000 make up
```

## 🏗️ Architecture

```text
┌────────────────────────────────────────────┐
│        Bot Swarm System                    │
├────────────────────────────────────────────┤
│                                            │
│  Server (Flask + SocketIO)                 │
│  ├─ WebSocket handling                     │
│  ├─ Room management                        │
│  └─ Message relay                          │
│                                            │
│  Bot Swarm (12 Async Bots)                 │
│  ├─ Diverse personalities                  │
│  ├─ AI-powered responses                   │
│  ├─ Social tracking                        │
│  └─ LM integration                         │
│                                            │
│  Network: bot-network (bridge)             │
│                                            │
└────────────────────────────────────────────┘
```

## 🔌 Language Model Integration

To use local AI models:

1. Install [LM Studio](https://lmstudio.ai)
2. Load a model (e.g., Llama 3 8B Instruct)
3. Start the local server in LM Studio
4. Set in `.env`:

   ```bash
   LM_API=http://host.docker.internal:1234/v1/chat/completions
   ```

If LM is unavailable, bots fall back to template responses.

## 📊 Bot Personalities

- **Sarcastic Weeb** - Anime references and irony
- **Hype Beast** - Excited, emote-heavy
- **Lurker** - Minimal, rare comments
- **Toxic Troll** - Playful roasts
- **Wholesome Supporter** - Positive vibes
- **Meme Lord** - Internet references
- **Backseat Gamer** - Strategic advice
- **Coomer** - Simping humor
- **Pepega Viewer** - Confused reactions
- **Gigachad** - Hot takes
- **Anime Analyst** - Tier lists
- **Normie** - Out of touch

## 🧪 Testing

```bash
# Build images
make build

# Start services
make up

# Check health
curl http://localhost:5000/health

# View logs
make logs

# Cleanup
make down
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
SERVER_PORT=8000 make up
```

### Services Won't Start

```bash
make logs              # Check error logs
make clean             # Reset everything
make build && make up  # Rebuild and restart
```

### Out of Memory

```bash
NUM_BOTS=6 make up     # Reduce bot count
docker stats           # Monitor usage
```

## 📁 Project Structure

```text
.
├── server.py                    # Flask WebSocket server
├── bot_swarm.py                 # Bot orchestration
├── personas.py                  # Personality definitions (optional)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Multi-stage build
├── docker-compose.yml           # Service orchestration
├── docker-compose.override.yml  # Local dev config
├── .dockerignore                # Build optimization
├── .env.example                 # Config template
├── Makefile                     # Build commands
├── templates/
│   └── index.html               # Chat UI
├── static/
│   └── socket.io.min.js         # SocketIO client
└── emotes/
    └── emotes.json              # Emote cache
```

## 🚀 Deployment

### Docker Hub

```bash
make push-images
```

### Production Checklist

- Set resource limits in docker-compose
- Configure persistent volumes
- Set up log aggregation
- Use non-root user for container
- Enable restart policies
- Configure monitoring

## 📝 License

See LICENSE file.

## 🆘 Support

- Run `make help` for all available commands
- Check logs with `make logs`
- Read documentation in DOCKER_SETUP.md
- Review QUICKSTART.md for quick reference

## ✨ Next Steps

1. Start services: `make up`
2. View logs: `make logs`
3. Customize: `cp .env.example .env` and edit
4. Deploy: Use docker-compose to production

---

## Happy swarming! 🤖🚀

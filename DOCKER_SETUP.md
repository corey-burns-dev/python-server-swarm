# 🤖 Bot Swarm - Docker Setup Guide

A fully containerized Twitch-style chat bot swarm with diverse AI-powered personas.

## 📋 Quick Start

### Prerequisites
- Docker & Docker Compose (v3.8+)
- Make (optional, but recommended)
- ~2GB free disk space for images

### One-Command Start
```bash
make build && make up
```

Or without make:
```bash
docker-compose build && docker-compose up -d
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Bot Swarm System                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐          ┌──────────────────┐   │
│  │   Flask Server   │ ◄────────┤   Bot Swarm      │   │
│  │  (Port 5000)     │ WebSocket│   (12 Bots)      │   │
│  │  - SocketIO      │          │  - Async bots    │   │
│  │  - Room mgmt     │          │  - LM integration│   │
│  │  - Chat relay    │          │  - Personalities │   │
│  └──────────────────┘          └──────────────────┘   │
│                                                          │
│  Network: bot-network (bridge)                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 📖 Usage

### Build Images
```bash
# Build both images
make build

# Build specific image
make build-server
make build-swarm
```

### Start Services
```bash
# Start in background
make up

# Follow logs
make logs

# View status
make status
```

### Stop Services
```bash
# Stop all services (keeps volumes)
make down

# Full cleanup (removes containers + volumes)
make clean

# Remove everything including images
make clean-all
```

### View Logs
```bash
# All services
make logs

# Specific service
make logs-server
make logs-swarm
```

### Debugging
```bash
# Open shell in container
make shell-server
make shell-swarm

# List containers
make ps
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Key variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | 5000 | HTTP port for Flask server |
| `NUM_BOTS` | 12 | Number of bot personalities |
| `LM_API` | `http://localhost:1234/v1/chat/completions` | Language model API endpoint |
| `NUM_BOTS` | 12 | Number of bots to spawn |
| `TEMPERATURE` | 0.85 | LM temperature (creativity) |
| `MAX_TOKENS` | 60 | Max tokens per response |
| `ROOM_ID` | `test-room-123` | Default chat room |

### Launch with Custom Config
```bash
# Via environment file
docker-compose --env-file .env up -d

# Via command line
NUM_BOTS=24 docker-compose up -d
```

## 🌐 Access Services

Once running:

| Service | URL | Purpose |
|---------|-----|---------|
| Server | `http://localhost:5000` | Chat UI |
| Health | `http://localhost:5000/health` | Health check |
| WebSocket | ws://localhost:5000/socket.io/ | Bot connections |

### Health Check
```bash
# Check server health
curl http://localhost:5000/health

# Response:
# {"status": "healthy", "rooms": 1, "sessions": 13}
```

## 📊 Monitoring

### View Live Status
```bash
make status
```

### Stream Logs
```bash
# All logs
make logs

# Server only
make logs-server

# Bots only
make logs-swarm

# Filter by keyword
docker-compose logs | grep "persona"
```

### Check Container Resources
```bash
docker stats
```

## 🐍 Local Development

### Run Without Docker
```bash
# Terminal 1: Server
make dev-run
# OR: python server.py

# Terminal 2: Bots
python bot_swarm.py
```

### Hot Reload in Docker
The `docker-compose.override.yml` mounts local source files. Changes to `.py` files are reflected in running containers:

```bash
# Edit code locally, changes appear in container immediately
make up
nano server.py  # Edit and save
# Changes reflected in running container
```

### Rebuild After Code Changes
```bash
make build && make restart
```

## 🔌 LM Studio Integration

To use local language models:

1. **Install LM Studio** - `https://lmstudio.ai`
2. **Load a model** (e.g., Llama 3 8B Instruct)
3. **Start the server** - LM Studio → Start Local Server
4. **Configure environment**:
   ```bash
   LM_API=http://host.docker.internal:1234/v1/chat/completions
   ```

The bots will use the LM for generating natural responses. If LM is unavailable, they fall back to template responses.

## 📦 Docker Images

### Image Details

**Base Layer:**
- Python 3.11 slim
- System dependencies (curl, nodejs)
- Python packages from requirements.txt
- Total size: ~400MB base

**Server Image:**
- Extends base
- Flask + SocketIO
- Health check enabled
- ~420MB total

**Swarm Image:**
- Extends base  
- Bot swarm with async
- LM integration
- ~420MB total

### View Images
```bash
docker images | grep bot-swarm
```

### Push to Registry
```bash
make push-images
```

## 🐛 Troubleshooting

### Server won't start
```bash
# Check logs
make logs-server

# Common issues:
# - Port 5000 already in use: change SERVER_PORT
# - Missing requirements: rebuild with `make build`
```

### Bots not connecting
```bash
# Check bot logs
make logs-swarm

# Verify server is healthy
curl http://localhost:5000/health

# Check network connectivity
docker network inspect bot-network
```

### Out of memory
```bash
# Reduce bot count
NUM_BOTS=6 docker-compose up -d

# Check current usage
docker stats
```

### Permission denied errors
```bash
# Ensure Docker daemon is running
docker ps

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
```

## 🚀 Production Deployment

### Pre-Deployment Checklist
- [ ] Build images with production tag: `docker build -t bot-swarm:v1.0 .`
- [ ] Test in staging environment
- [ ] Configure environment variables
- [ ] Set up log aggregation (optional)
- [ ] Configure backup/persistence volumes

### Production docker-compose
```yaml
services:
  server:
    restart: always
    # Add resource limits
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
    # Add persistent volume
    volumes:
      - server-data:/app/data
```

### Kubernetes Deployment (Optional)
See `k8s/` directory for Kubernetes manifests.

## 📝 File Structure

```
.
├── Dockerfile              # Multi-stage: base, server, swarm
├── docker-compose.yml      # Service orchestration
├── docker-compose.override.yml  # Local dev overrides
├── .dockerignore           # Exclude from build
├── .env.example            # Environment template
├── Makefile                # 30+ convenient commands
├── server.py               # Flask WebSocket server
├── bot_swarm.py            # Bot swarm orchestration
├── personas.py             # Bot personality definitions
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Chat UI
├── static/
│   └── socket.io.min.js    # SocketIO client
└── emotes/
    └── emotes.json         # 7TV emote cache
```

## 🤝 Contributing

Issues & improvements welcome! Run tests before submitting:

```bash
# Lint code
docker-compose exec server python -m py_compile server.py
docker-compose exec bot_swarm python -m py_compile bot_swarm.py

# Run basic tests
make build && make up && sleep 5 && make logs
```

## 📜 License

See LICENSE file.

## 🆘 Support

- **Issues**: Check Makefile help: `make help`
- **Logs**: Review service logs: `make logs`
- **Status**: Check services: `make status`
- **Docker Docs**: https://docs.docker.com

---

**Happy swarming! 🤖🚀**

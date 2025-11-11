# 🚀 Quick Start - Bot Swarm Docker

## One-Liner Start

```bash
make up
```

That's it! The bot swarm will:

1. ✅ Build Docker images (first time only)
2. ✅ Start Flask server on port 5000
3. ✅ Spawn 12 AI-powered bot personalities
4. ✅ Begin chatting in the room

## Check It's Working

```bash
# View status
make status

# Watch live logs
make logs

# Check health
curl http://localhost:5000/health
```

## Commands Quick Reference

| Command | What it does |
|---------|------------|
| `make up` | Start everything |
| `make down` | Stop everything |
| `make logs` | Watch live logs |
| `make status` | Check service status |
| `make restart` | Restart all services |
| `make clean` | Delete containers & volumes |
| `make shell-server` | Debug server container |
| `make shell-swarm` | Debug bot container |

## Access

| Service | URL |
|---------|-----|
| Chat UI | `http://localhost:5000` |
| Health Check | `http://localhost:5000/health` |

## Stop It

```bash
make down
```

## Full Cleanup

```bash
make clean
```

## More Help

```bash
make help
```

## Customize Before Starting

Copy and edit `.env`:

```bash
cp .env.example .env
# Edit .env with your settings
# Then: make up
```

**Key settings:**

- `NUM_BOTS=12` - Number of AI personalities
- `LM_API=http://localhost:1234/v1/chat/completions` - Point to local LM Studio
- `SERVER_PORT=5000` - Change HTTP port if needed

---

## That's all! Happy chatting with 12 AI bots! 🤖🚀

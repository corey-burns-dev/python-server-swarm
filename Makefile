.PHONY: help build build-server build-swarm up down restart clean logs logs-server logs-swarm \
        shell-server shell-swarm status ps push-images pull-images dev-run dev-down

# ============================================================================
# Variables
# ============================================================================
REGISTRY ?= docker.io
IMAGE_NAME ?= bot-swarm
DOCKER_COMPOSE = docker-compose
DOCKER = docker

VERSION ?= latest
SERVER_PORT ?= 5000
NUM_BOTS ?= 12
LM_API ?= http://localhost:1234/v1/chat/completions

# ============================================================================
# Help
# ============================================================================
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║        🤖 Bot Swarm Docker - Makefile Commands               ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 BUILD TARGETS:"
	@echo "  make build              - Build both server and swarm images"
	@echo "  make build-server       - Build only server image"
	@echo "  make build-swarm        - Build only swarm image"
	@echo ""
	@echo "🚀 RUNNING:"
	@echo "  make up                 - Start all services (server + swarm)"
	@echo "  make down               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo "  make status             - Show status of all containers"
	@echo ""
	@echo "📋 LOGS:"
	@echo "  make logs               - Follow logs from all services"
	@echo "  make logs-server        - Follow server logs only"
	@echo "  make logs-swarm         - Follow swarm logs only"
	@echo ""
	@echo "🔧 DEBUGGING:"
	@echo "  make shell-server       - Open shell in server container"
	@echo "  make shell-swarm        - Open shell in swarm container"
	@echo "  make ps                 - List all containers"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean              - Remove all containers and volumes"
	@echo "  make clean-images       - Remove all images"
	@echo "  make clean-all          - Remove containers, volumes, and images"
	@echo ""
	@echo "🐍 LOCAL DEVELOPMENT:"
	@echo "  make dev-run            - Run server locally (not in Docker)"
	@echo "  make dev-down           - Kill local dev server"
	@echo ""
	@echo "📤 REGISTRY:"
	@echo "  make push-images        - Push images to registry"
	@echo "  make pull-images        - Pull images from registry"
	@echo ""
	@echo "Environment variables:"
	@echo "  SERVER_PORT=${SERVER_PORT}     - Server port (default: 5000)"
	@echo "  NUM_BOTS=${NUM_BOTS}          - Number of bots (default: 12)"
	@echo "  LM_API=${LM_API}"
	@echo ""

# ============================================================================
# Build targets
# ============================================================================
build: build-server build-swarm
	@echo "✅ Both images built successfully!"

build-server:
	@echo "🔨 Building server image..."
	$(DOCKER_COMPOSE) build server
	@echo "✅ Server image built!"

build-swarm:
	@echo "🔨 Building swarm image..."
	$(DOCKER_COMPOSE) build bot_swarm
	@echo "✅ Swarm image built!"

# ============================================================================
# Running services
# ============================================================================
up:
	@echo "🚀 Starting bot swarm..."
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "✅ Services started!"
	@echo ""
	@echo "📊 Status:"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "🌐 Access:"
	@echo "   Server: http://localhost:$(SERVER_PORT)"
	@echo "   API Health: http://localhost:$(SERVER_PORT)/health"
	@echo ""
	@echo "📝 View logs: make logs"

down:
	@echo "⬇️  Stopping bot swarm..."
	$(DOCKER_COMPOSE) down
	@echo "✅ Services stopped!"

restart: down up

ps:
	@$(DOCKER_COMPOSE) ps

status:
	@echo "📊 Service Status:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(DOCKER_COMPOSE) ps
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📈 Container Stats:"
	@$(DOCKER) stats --no-stream $(shell $(DOCKER_COMPOSE) ps -q) || echo "No containers running"

# ============================================================================
# Logging
# ============================================================================
logs:
	@echo "📝 Following logs from all services (Ctrl+C to exit)..."
	@$(DOCKER_COMPOSE) logs -f

logs-server:
	@echo "📝 Following server logs (Ctrl+C to exit)..."
	@$(DOCKER_COMPOSE) logs -f server

logs-swarm:
	@echo "📝 Following bot swarm logs (Ctrl+C to exit)..."
	@$(DOCKER_COMPOSE) logs -f bot_swarm

# ============================================================================
# Debugging & Shell access
# ============================================================================
shell-server:
	@echo "🔧 Opening shell in server container..."
	@$(DOCKER_COMPOSE) exec server /bin/bash

shell-swarm:
	@echo "🔧 Opening shell in swarm container..."
	@$(DOCKER_COMPOSE) exec bot_swarm /bin/bash

# ============================================================================
# Cleanup
# ============================================================================
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	$(DOCKER_COMPOSE) down --volumes --remove-orphans
	@echo "✅ Cleanup complete!"

clean-images:
	@echo "🧹 Removing images..."
	$(DOCKER_COMPOSE) down --rmi all
	@echo "✅ Images removed!"

clean-all: clean clean-images
	@echo "🧹 Running full system prune..."
	$(DOCKER) system prune -f --volumes
	@echo "✅ Full cleanup complete!"

# ============================================================================
# Local development (no Docker)
# ============================================================================
dev-run:
	@echo "🚀 Starting server locally..."
	@python server.py &
	@SERVER_PID=$$!
	@echo "✅ Server started (PID: $$SERVER_PID)"
	@echo "🤖 In another terminal, run: python bot_swarm.py"

dev-down:
	@echo "⬇️  Killing local dev server..."
	@pkill -f "python server.py" && echo "✅ Server killed" || echo "❌ No running server found"

# ============================================================================
# Registry operations
# ============================================================================
push-images:
	@echo "📤 Pushing images to registry..."
	$(DOCKER) tag bot-swarm:latest $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	$(DOCKER) push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	@echo "✅ Images pushed!"

pull-images:
	@echo "📥 Pulling images from registry..."
	$(DOCKER) pull $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	@echo "✅ Images pulled!"
# ============================================================================
# Multi-stage build: base layer with dependencies
# ============================================================================
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies (including curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  nodejs \
  npm \
  && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app

# ============================================================================
# Server image: runs Flask + SocketIO
# ============================================================================
FROM base as server

ENV FLASK_ENV=production
ENV PORT=5000

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "server.py"]

# ============================================================================
# Swarm image: runs bot_swarm
# ============================================================================
FROM base as swarm

ENV SERVER_URL=http://server:5000
ENV LM_API=http://localhost:1234/v1/chat/completions
ENV NUM_BOTS=12
ENV MAX_TOKENS=60
ENV TEMPERATURE=0.85

CMD ["python", "bot_swarm.py"]
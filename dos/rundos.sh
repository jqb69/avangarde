#!/bin/bash

# dos/rundos.sh
set -e

APP_DIR="/home/openclaw/openclaw"
COMPOSE_FILE="docker-compose.yml"

setup_environment() {
    echo "→ Initializing Deployment Directory..."

    if [ ! -d "$APP_DIR" ]; then
        echo "  └─ Creating $APP_DIR..."
        mkdir -p "$APP_DIR"
    fi
    
    cd "$APP_DIR" || { echo "❌ Critical: Could not access $APP_DIR"; exit 1; }

    local FALLBACK_USER="openclaw"
    local FALLBACK_REDIS="redis://redis:6379/0"

    if [ -f .env ]; then
        echo "  └─ Loading existing .env..."
        set -a
        source .env
        set +a
    fi

    # Write .env (GitHub env vars take priority via ${VAR:-fallback})
    {
        echo "DOCKER_HUB_USER=${DOCKER_HUB_USER:-$FALLBACK_USER}"
        echo "REDIS_URL=${REDIS_URL:-$FALLBACK_REDIS}"
        echo "PYTHONUNBUFFERED=1"
    } > .env

    echo "  └─ Creating volume directories..."
    mkdir -p data logs
}

pull_latest_image() {
    local hub_user="${DOCKER_HUB_USER:-openclaw}"
    local image="${hub_user}/openclaw:latest"
    echo "→ Pulling: $image"
    docker pull "$image"
}

deploy_services() {
    echo "→ Deploying..."
    docker-compose -f "$COMPOSE_FILE" pull
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
}

verify_status() {
    echo "→ Waiting..."
    sleep 3
    docker-compose ps
    docker-compose logs --tail=20
}

main() {
    echo "=== OpenClaw Deployment Started ==="
    setup_environment
    pull_latest_image
    deploy_services
    verify_status
    echo "=== Completed ==="
}

main

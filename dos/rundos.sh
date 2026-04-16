#!/bin/bash

# dos/rundos.sh
set -e

APP_DIR="/home/openclaw/openclaw"
COMPOSE_FILE="docker-compose.yml"

setup_environment() {
    echo "→ Initializing Deployment Directory..."

    # 1. Create the directory if it's missing (The "First-Run" fix)
    if [ ! -d "$APP_DIR" ]; then
        echo "  └─ Directory $APP_DIR not found. Creating it now..."
        mkdir -p "$APP_DIR"
    fi
    
    cd "$APP_DIR" || { echo "❌ Critical: Could not access $APP_DIR"; exit 1; }

    # 2. Define Fallbacks (Priority: GitHub Secret > Existing .env > Fallback)
    local FALLBACK_USER="openclaw"
    local FALLBACK_REDIS="redis://redis:6379/0"
    local FALLBACK_MODE="api"

    # 3. Load existing .env if it exists to preserve manual tweaks
    if [ -f .env ]; then
        echo "  └─ Existing .env found. Merging values..."
        set -a
        source .env
        set +a
    fi

    # 4. Generate/Update .env with current variables or fallbacks
    # This uses the ${VAR:-DEFAULT} logic you wanted
    {
        echo "DOCKER_HUB_USER=${DOCKER_HUB_USER:-$FALLBACK_USER}"
        echo "REDIS_URL=${REDIS_URL:-$FALLBACK_REDIS}"
        echo "MODE=${MODE:-$FALLBACK_MODE}"
        echo "PYTHONUNBUFFERED=1"
    } > .env

    # 5. Create sub-directories for Docker Volumes
    echo "  └─ Ensuring volume directories exist..."
    mkdir -p data logs
}

pull_latest_image() {
    local hub_user="${DOCKER_HUB_USER:-openclaw}"
    local image="${hub_user}/openclaw:latest"
    echo "→ Pulling: $image"
    docker pull "$image"
}

deploy_services() {
    echo "→ Deploying containers..."
    docker-compose -f "$COMPOSE_FILE" pull
    docker-compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
}

verify_status() {
    echo "→ Waiting for services..."
    sleep 3
    echo "→ Container Status:"
    docker-compose ps
    echo "→ Logs:"
    docker-compose logs --tail=20
}

main() {
    echo "=== OpenClaw Deployment Started ==="
    setup_environment
    pull_latest_image
    deploy_services
    verify_status
    echo "=== Deployment completed ==="
}

main

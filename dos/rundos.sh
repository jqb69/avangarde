#!/bin/bash
# do/rundos.sh
# --- Global Settings ---
# -e: Exit on error, -u: Error on unset vars, -o pipefail: Catch errors in pipes
set -euo pipefail

# --- Configuration ---
ENV_FILE=".env"


# --- Functions ---

load_env() {
    echo "📂 Step 1: Handling Environment..."
    
    # Lowercase the actor name for the image path
    local ACTOR_LOWER=$(echo "$GH_ACTOR" | tr '[:upper:]' '[:lower:]')
    export IMAGE_NAME="ghcr.io/${ACTOR_LOWER}/avangarde:latest"

    # STRIP HIDDEN CHARACTERS from the token immediately
    CLEAN_TOKEN=$(echo "$GH_TOKEN" | tr -d '[:space:]')

    echo "📂 Step 1: Handling Environment..."
    # Now we write .env directly to the root (~/avangarde/.env)
    {
        echo "TG_SESSION_STR=${TG_SESSION_STR}"
        echo "TG_API_ID=${TG_API_ID}"
        echo "TG_API_HASH=${TG_API_HASH}"
        echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}"
        echo "GH_TOKEN=$(echo "$GH_TOKEN" | tr -d '[:space:]')"
        echo "GH_ACTOR=${GH_ACTOR}"
        echo "IMAGE_NAME=${IMAGE_NAME}"
    } > "$ENV_FILE"
    
    chmod 600 "$ENV_FILE"
    echo "✅ .env updated successfully."
    
    # Export for current shell and Docker Compose
    set -a; source "$ENV_FILE"; set +a
}

check_system() {
    echo "🔍 Step 2: System Integrity Check..."
    
    # 1. STRIP EVERYTHING: Remove potential hidden spaces/newlines from the secret
    # Sometimes copying from the browser adds a trailing newline
    CLEAN_TOKEN=$(echo "$GH_TOKEN" | tr -d '[:space:]')
    
    # 2. Get lowercased names
    local ACTOR_LC=$(echo "$GH_ACTOR" | tr '[:upper:]' '[:lower:]')
    local OWNER_LC=$(echo "jqb69" | tr '[:upper:]' '[:lower:]')

    # 1. Install Docker if missing
    if ! [ -x "$(command -v docker)" ]; then
        echo "📦 Docker not found. Installing..."
        curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
    fi

    # 2. Handle Docker Compose (V1 or V2)
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
        echo "✅ Found Docker Compose V2"
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "✅ Found Docker Compose V1"
    else
        echo "📦 Docker Compose not found. Installing V2 Plugin..."
        # Note: apt-get update might fail if not sudo/root, 
        # but since this is a Droplet, you're likely root.
        sudo apt-get update && sudo apt-get install -y docker-compose-plugin
        DOCKER_COMPOSE_CMD="docker compose"
    fi
    
    export DOCKER_COMPOSE_CMD
    echo "🔑 Attempting Multi-Stage Authentication..."

    # Attempt 1: Using the Actor (jqb69)
    if echo "$CLEAN_TOKEN" | docker login ghcr.io -u "$ACTOR_LC" --password-stdin 2>/dev/null; then
        echo "✅ SUCCESS: Authenticated as $ACTOR_LC"
    
    # Attempt 2: Using the Owner name directly
    elif echo "$CLEAN_TOKEN" | docker login ghcr.io -u "$OWNER_LC" --password-stdin 2>/dev/null; then
        echo "✅ SUCCESS: Authenticated as $OWNER_LC"

    # Attempt 3: The 'Secret' Trick (Using the token AS the username)
    # Some registries allow the PAT as the username if the scope is dedicated
    elif echo "$CLEAN_TOKEN" | docker login ghcr.io -u "$CLEAN_TOKEN" --password-stdin 2>/dev/null; then
        echo "✅ SUCCESS: Authenticated via Token-String"

    else
        echo "❌ FATAL: All login attempts denied."
        echo "DEBUG: Token length is ${#CLEAN_TOKEN}. If this is 40, the token is technically valid."
        echo "This usually means the PAT wasn't RE-SAVED after the Package Admin was set."
        exit 1
    fi
}

deploy_config_yaml() {
    local staged="${ROOT_DIR}/config.yaml"
    local live="${ROOT_DIR}/config.yaml"
    local stamp="${ROOT_DIR}/.config.yaml.deployed_mtime"

    if [[ ! -f "$staged" ]]; then
        echo "⚠️ No config.yaml in $ROOT_DIR — skip"
        return 0
    fi

    if [[ ! -f "$live" ]]; then
        chmod 644 "$staged"
        stat -c %Y "$staged" > "$stamp" 2>/dev/null || stat -f %m "$staged" > "$stamp"
        echo "✅ config.yaml installed (missing)"
        return 0
    fi

    local src_m dst_m
    src_m=$(stat -c %Y "$staged" 2>/dev/null || stat -f %m "$staged")
    dst_m=$(cat "$stamp" 2>/dev/null || echo 0)

    if [[ "$src_m" -gt "$dst_m" ]]; then
        # staged was replaced by SCP with a newer file
        chmod 644 "$staged"
        echo "$src_m" > "$stamp"
        echo "✅ config.yaml refreshed from deploy bundle"
    else
        echo "✓ config.yaml kept (not newer than last deploy)"
    fi
}

deploy_openclaw() {
    echo "📍 Working Directory: $(pwd)"
    local ROOT_DIR
    ROOT_DIR="$(pwd)"

    if [[ ! -f "docker-compose.yml" ]]; then
        echo "❌ docker-compose.yml missing in $ROOT_DIR"
        exit 1
    fi

    docker pull "${IMAGE_NAME}"

    # 1) Image must import yaml + parsers (catches stale GHCR)
    if ! docker run --rm --entrypoint python "${IMAGE_NAME}" \
        -c "import yaml; import utils.parsers; print('image_ok')"; then
        echo "❌ Pulled image failed import check — STALE_OR_BAD_IMAGE"
        exit 1
    fi

    # 2) Config must load with the same mount compose uses
    if [[ ! -f "${ROOT_DIR}/config.yaml" ]]; then
        echo "❌ ${ROOT_DIR}/config.yaml missing — SCP/deploy did not deliver it"
        exit 1
    fi
    if ! docker run --rm \
        -v "${ROOT_DIR}/config.yaml:/app/config.yaml:ro" \
        --entrypoint python "${IMAGE_NAME}" \
        -c "import utils.config_loader; print('config_ok')"; then
        echo "❌ Image cannot load mounted config.yaml — abort"
        exit 1
    fi

    docker stop openclaw-agent openclaw-api openclaw-redis 2>/dev/null || true
    docker rm openclaw-agent openclaw-api openclaw-redis 2>/dev/null || true

    if [[ "${WIPE_REDIS:-0}" == "1" ]]; then
        echo "🧹 WIPE_REDIS=1 — removing avangarde_redis_data"
        docker volume rm avangarde_redis_data 2>/dev/null || true
    fi

    $DOCKER_COMPOSE_CMD pull
    $DOCKER_COMPOSE_CMD up -d --remove-orphans --force-recreate
}




cleanup() {
    echo "🧹 Step 5: Post-Deployment Cleanup..."
    # Remove old images to save disk space on the Droplet
    docker image prune -f
}

# --- Main Logic Loop ---

main() {
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$ROOT_DIR"
    echo "🏁 Starting Deployment..."
    
    load_env
    check_system
    #deploy_config_yaml
    #deploy_redis
    deploy_openclaw
    cleanup
    echo "=============================================="
    echo "🎉 SUCCESS: Compose stack is up and running."
    echo "Check logs with: docker-compose logs -f"
    echo "🎉 SUCCESS: OpenClaw Sniper and API are running."
}

# Execute main
main

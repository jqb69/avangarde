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

    echo "🔄 Overwriting .env with fresh secrets..."
    {
        echo "TG_SESSION_STR=${TG_SESSION_STR}"
        echo "TG_API_ID=${TG_API_ID}"
        echo "TG_API_HASH=${TG_API_HASH}"
        echo "IMAGE_NAME=${IMAGE_NAME}"
        echo "GH_TOKEN=${CLEAN_TOKEN}"
        echo "GH_ACTOR=${GH_ACTOR}"
        echo "REDIS_URL=redis://127.0.0.1:6379/0"
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

deploy_openclaw() {
    echo "🧹 Step 3: Cleaning up legacy manual containers..."
    docker stop openclaw-agent openclaw-api claw-redis 2>/dev/null || true
    docker rm openclaw-agent openclaw-api claw-redis 2>/dev/null || true

    # FIX: Corrected 'ecd' to 'cd'
    cd "$(dirname "$0")/.." 
    
    echo "🏗️ Step 4: Orchestrating with Docker Compose..."
    docker-compose pull
    docker-compose up -d --remove-orphans --force-recreate
}

deploy_containers() {
    echo "🚀 Step 4: Deploying OpenClaw..."
    
    # Always pull the latest image before restarting
    docker pull "$IMAGE_NAME"

    # --- Start Sniper Agent ---
    echo "🎯 Refreshing Sniper Agent..."
    docker stop openclaw-agent 2>/dev/null || true
    docker rm openclaw-agent 2>/dev/null || true
    docker run -d \
      --name openclaw-agent \
      --env MODE=agent \
      --env-file "$ENV_FILE" \
      --network host \
      --restart unless-stopped \
      "$IMAGE_NAME" python3 main.py

    # --- Start Web API ---
    echo "🌐 Refreshing Web API..."
    docker stop openclaw-api 2>/dev/null || true
    docker rm openclaw-api 2>/dev/null || true
    docker run -d \
      --name openclaw-api \
      --env MODE=api \
      --env-file "$ENV_FILE" \
      --network host \
      -p 80:80 \
      --restart unless-stopped \
      "$IMAGE_NAME" gunicorn -w 4 -b 0.0.0.0:80 main:app
}

cleanup() {
    echo "🧹 Step 5: Post-Deployment Cleanup..."
    # Remove old images to save disk space on the Droplet
    docker image prune -f
}

# --- Main Logic Loop ---

main() {
    echo "🏁 Starting Deployment..."
    
    load_env
    check_system
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

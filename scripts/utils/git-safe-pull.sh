#!/bin/bash
# Safe git pull with retry logic and error handling
# This script wraps git pull operations with proper timeout and retry mechanisms

set -e

# Default values
REMOTE="${1:-origin}"
BRANCH="${2:-main}"
MAX_RETRIES="${3:-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_info "Current branch: $CURRENT_BRANCH"

# Use git-fetch-with-retry if available
if [ -f "$SCRIPT_DIR/git-fetch-with-retry.sh" ]; then
    log_info "Using git-fetch-with-retry.sh for improved reliability"

    # Fetch with retry logic
    if ! "$SCRIPT_DIR/git-fetch-with-retry.sh" --remote "$REMOTE" --branch "$BRANCH" --retries "$MAX_RETRIES"; then
        log_error "Failed to fetch from $REMOTE/$BRANCH"
        exit 1
    fi

    # Merge the fetched changes
    log_info "Merging changes from $REMOTE/$BRANCH"
    if ! git merge "$REMOTE/$BRANCH" --ff-only 2>&1; then
        log_warning "Fast-forward merge not possible, attempting regular merge"
        git merge "$REMOTE/$BRANCH"
    fi
else
    # Fallback to regular git pull with basic retry
    log_warning "git-fetch-with-retry.sh not found, using basic retry logic"

    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_RETRIES ]; do
        ATTEMPT=$((ATTEMPT + 1))
        log_info "Attempt $ATTEMPT/$MAX_RETRIES: Pulling from $REMOTE/$BRANCH"

        # Set timeout configurations
        export GIT_HTTP_CONNECT_TIMEOUT=10
        export GIT_HTTP_LOW_SPEED_LIMIT=1000
        export GIT_HTTP_LOW_SPEED_TIME=30

        # Try git pull with timeout
        if timeout 120 git pull "$REMOTE" "$BRANCH" 2>&1; then
            log_info "Git pull completed successfully"
            exit 0
        else
            EXIT_CODE=$?
            if [ $EXIT_CODE -eq 124 ]; then
                log_warning "Git pull failed (attempt $ATTEMPT/$MAX_RETRIES): Timeout after 120 seconds"
            else
                log_warning "Git pull failed (attempt $ATTEMPT/$MAX_RETRIES): Exit code $EXIT_CODE"
            fi

            if [ $ATTEMPT -lt $MAX_RETRIES ]; then
                log_info "Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done

    log_error "Failed to pull from $REMOTE/$BRANCH after $MAX_RETRIES attempts"
    exit 1
fi

log_info "Git pull operation completed successfully"
exit 0
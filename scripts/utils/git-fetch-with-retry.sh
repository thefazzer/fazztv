#!/bin/bash
# Git fetch with timeout and retry logic

set -e

# Default values
MAX_RETRIES=3
TIMEOUT_SECONDS=120  # 2 minutes default
RETRY_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
REMOTE="origin"
BRANCH="main"

while [[ $# -gt 0 ]]; do
    case $1 in
        --remote)
            REMOTE="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT_SECONDS="$2"
            shift 2
            ;;
        --retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --remote REMOTE      Remote to fetch from (default: origin)"
            echo "  --branch BRANCH      Branch to fetch (default: main)"
            echo "  --timeout SECONDS    Timeout in seconds (default: 120)"
            echo "  --retries COUNT      Maximum retries (default: 3)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to perform git fetch with timeout
git_fetch_with_timeout() {
    local attempt=$1
    echo -e "${YELLOW}Attempt $attempt/$MAX_RETRIES: Fetching from $REMOTE (branch: $BRANCH)...${NC}"

    # Set git timeout configurations temporarily
    export GIT_HTTP_CONNECT_TIMEOUT=10
    export GIT_HTTP_LOW_SPEED_LIMIT=1000
    export GIT_HTTP_LOW_SPEED_TIME=30

    # Run git fetch with timeout
    if timeout "$TIMEOUT_SECONDS" git fetch "$REMOTE" "$BRANCH" --verbose 2>&1; then
        echo -e "${GREEN}✓ Git fetch completed successfully${NC}"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            echo -e "${RED}✗ Git fetch timed out after ${TIMEOUT_SECONDS} seconds${NC}"
        else
            echo -e "${RED}✗ Git fetch failed with exit code: $exit_code${NC}"
        fi
        return $exit_code
    fi
}

# Main retry loop
for attempt in $(seq 1 $MAX_RETRIES); do
    if git_fetch_with_timeout $attempt; then
        exit 0
    fi

    if [[ $attempt -lt $MAX_RETRIES ]]; then
        echo -e "${YELLOW}Retrying in ${RETRY_DELAY} seconds...${NC}"
        sleep $RETRY_DELAY
        # Increase timeout for subsequent attempts
        TIMEOUT_SECONDS=$((TIMEOUT_SECONDS + 30))
    fi
done

echo -e "${RED}ERROR: Failed to fetch from $REMOTE after $MAX_RETRIES attempts${NC}"
exit 1
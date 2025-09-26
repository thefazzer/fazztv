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
    echo -e "${YELLOW}[INFO] Attempt $attempt/$MAX_RETRIES: Fetching from $REMOTE (branch: $BRANCH)...${NC}"

    # Set git timeout configurations temporarily
    export GIT_HTTP_CONNECT_TIMEOUT=10
    export GIT_HTTP_LOW_SPEED_LIMIT=1000
    export GIT_HTTP_LOW_SPEED_TIME=30

    # Capture git fetch output
    local git_output
    local git_error_file="/tmp/git-fetch-error-$$"

    # Run git fetch with timeout
    if timeout "$TIMEOUT_SECONDS" git fetch "$REMOTE" "$BRANCH" --verbose 2>"$git_error_file"; then
        echo -e "${GREEN}[SUCCESS] Git fetch completed successfully${NC}"
        rm -f "$git_error_file"
        return 0
    else
        local exit_code=$?
        local git_error=$(cat "$git_error_file" 2>/dev/null)

        if [[ $exit_code -eq 124 ]]; then
            echo -e "${YELLOW}[WARNING] Git fetch failed (attempt $attempt/$MAX_RETRIES): Timeout after ${TIMEOUT_SECONDS} seconds${NC}"
        else
            # Check for specific error patterns
            if echo "$git_error" | grep -q "fatal: unable to access"; then
                echo -e "${YELLOW}[WARNING] Git fetch failed (attempt $attempt/$MAX_RETRIES): fatal: unable to access '$(echo "$git_error" | grep -o "https://[^']*" | head -1)'${NC}"
            elif echo "$git_error" | grep -q "Connection timed out"; then
                echo -e "${YELLOW}[WARNING] Git fetch failed (attempt $attempt/$MAX_RETRIES): Connection timed out${NC}"
            elif echo "$git_error" | grep -q "Could not resolve host"; then
                echo -e "${YELLOW}[WARNING] Git fetch failed (attempt $attempt/$MAX_RETRIES): Could not resolve host${NC}"
            else
                echo -e "${YELLOW}[WARNING] Git fetch failed (attempt $attempt/$MAX_RETRIES): Exit code $exit_code${NC}"
            fi

            # Show detailed error if verbose
            if [[ -n "$git_error" ]]; then
                echo -e "${RED}[ERROR] Details: $git_error${NC}"
            fi
        fi

        rm -f "$git_error_file"
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

echo -e "${RED}[ERROR] Failed to fetch from $REMOTE after $MAX_RETRIES attempts${NC}"
echo -e "${RED}[ERROR] Please check your network connection and repository access${NC}"
exit 1
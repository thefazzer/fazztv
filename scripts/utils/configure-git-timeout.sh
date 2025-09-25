#!/bin/bash
# Configure git timeout settings to prevent fetch timeouts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default timeout values (in seconds)
DEFAULT_HTTP_TIMEOUT=300  # 5 minutes
DEFAULT_LOW_SPEED_TIME=60  # 1 minute
DEFAULT_LOW_SPEED_LIMIT=1000  # 1KB/s

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Configure git timeout settings to prevent fetch/pull/push timeouts

OPTIONS:
    -h, --help           Show this help message
    -s, --show           Show current git timeout configuration
    -a, --apply          Apply recommended timeout settings
    -r, --reset          Reset to default git settings
    --aggressive         Apply aggressive timeout settings for slow connections

EXAMPLES:
    $0 --show            # Show current settings
    $0 --apply           # Apply recommended settings
    $0 --aggressive      # Apply settings for very slow connections

EOF
    exit 0
}

show_current() {
    echo -e "${BLUE}=== Current Git Timeout Configuration ===${NC}"
    echo ""

    # HTTP timeout settings
    echo -e "${YELLOW}HTTP Settings:${NC}"
    http_timeout=$(git config --get http.postBuffer 2>/dev/null || echo "not set")
    echo "  http.postBuffer: $http_timeout"

    low_speed_limit=$(git config --get http.lowSpeedLimit 2>/dev/null || echo "not set")
    echo "  http.lowSpeedLimit: $low_speed_limit"

    low_speed_time=$(git config --get http.lowSpeedTime 2>/dev/null || echo "not set")
    echo "  http.lowSpeedTime: $low_speed_time"

    # Core settings
    echo -e "${YELLOW}Core Settings:${NC}"
    compression=$(git config --get core.compression 2>/dev/null || echo "not set")
    echo "  core.compression: $compression"

    pack_threads=$(git config --get pack.threads 2>/dev/null || echo "not set")
    echo "  pack.threads: $pack_threads"

    # Environment variables
    echo -e "${YELLOW}Environment Variables:${NC}"
    echo "  GIT_HTTP_CONNECT_TIMEOUT: ${GIT_HTTP_CONNECT_TIMEOUT:-not set}"
    echo "  GIT_HTTP_LOW_SPEED_LIMIT: ${GIT_HTTP_LOW_SPEED_LIMIT:-not set}"
    echo "  GIT_HTTP_LOW_SPEED_TIME: ${GIT_HTTP_LOW_SPEED_TIME:-not set}"
    echo ""
}

apply_settings() {
    local aggressive=$1

    echo -e "${GREEN}Applying git timeout configuration...${NC}"
    echo ""

    if [[ "$aggressive" == "true" ]]; then
        echo -e "${YELLOW}Using aggressive settings for slow connections${NC}"
        # Very generous timeouts for slow connections
        git config --global http.postBuffer 524288000  # 500MB
        git config --global http.lowSpeedLimit 100     # 100 bytes/s
        git config --global http.lowSpeedTime 600      # 10 minutes
        git config --global core.compression 0         # Disable compression
        git config --global pack.threads 1             # Single thread
    else
        echo -e "${GREEN}Using standard recommended settings${NC}"
        # Standard recommended settings
        git config --global http.postBuffer 157286400  # 150MB
        git config --global http.lowSpeedLimit 1000    # 1KB/s
        git config --global http.lowSpeedTime 60       # 1 minute
        git config --global core.compression -1        # Default compression
    fi

    echo ""
    echo -e "${GREEN}✓ Git timeout settings applied successfully${NC}"
    echo ""
    echo "Additionally, you can set these environment variables in your shell:"
    echo -e "${YELLOW}export GIT_HTTP_CONNECT_TIMEOUT=300${NC}  # 5 minutes"
    echo -e "${YELLOW}export GIT_HTTP_LOW_SPEED_LIMIT=1000${NC} # 1KB/s"
    echo -e "${YELLOW}export GIT_HTTP_LOW_SPEED_TIME=60${NC}    # 1 minute"
    echo ""
}

reset_settings() {
    echo -e "${YELLOW}Resetting git timeout configuration to defaults...${NC}"
    echo ""

    git config --global --unset http.postBuffer 2>/dev/null || true
    git config --global --unset http.lowSpeedLimit 2>/dev/null || true
    git config --global --unset http.lowSpeedTime 2>/dev/null || true
    git config --global --unset core.compression 2>/dev/null || true
    git config --global --unset pack.threads 2>/dev/null || true

    echo -e "${GREEN}✓ Git timeout settings reset to defaults${NC}"
    echo ""
}

# Parse command line arguments
if [[ $# -eq 0 ]]; then
    show_usage
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            ;;
        -s|--show)
            show_current
            exit 0
            ;;
        -a|--apply)
            apply_settings "false"
            exit 0
            ;;
        --aggressive)
            apply_settings "true"
            exit 0
            ;;
        -r|--reset)
            reset_settings
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
    shift
done
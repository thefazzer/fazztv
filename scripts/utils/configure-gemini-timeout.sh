#!/bin/bash
# Configure Gemini MCP timeout helper script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Current defaults
DEFAULT_TIMEOUT=21600  # 6 hours
COMPLEXITY_MULTIPLIER=1.5  # 50% increase for high complexity

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Configure HOLLOW_CD_GEMINI_MCP_TIMEOUT environment variable

OPTIONS:
    -h, --help           Show this help message
    -s, --show           Show current timeout configuration
    -t, --timeout SECS   Set timeout in seconds
    -m, --minutes MINS   Set timeout in minutes
    -H, --hours HOURS    Set timeout in hours
    -r, --recommend      Recommend timeout based on workload
    -e, --export         Generate export command for shell

EXAMPLES:
    $0 --show                       # Show current settings
    $0 --hours 4                    # Set to 4 hours
    $0 --recommend large-codebase   # Get recommendation

WORKLOAD TYPES (for --recommend):
    small         - Small projects (<1000 files)
    medium        - Medium projects (1000-5000 files)
    large         - Large projects (5000-20000 files)
    enterprise    - Enterprise codebases (>20000 files)

EOF
    exit 0
}

show_current() {
    echo -e "${BLUE}=== Current Gemini MCP Timeout Configuration ===${NC}"
    echo ""

    # Check environment variable
    if [[ -n "${HOLLOW_CD_GEMINI_MCP_TIMEOUT}" ]]; then
        current=$HOLLOW_CD_GEMINI_MCP_TIMEOUT
        echo -e "${GREEN}✓${NC} HOLLOW_CD_GEMINI_MCP_TIMEOUT is set"
        echo -e "   Current value: ${YELLOW}${current}s${NC} ($(( current / 60 )) minutes / $(( current / 3600 )) hours)"
    else
        echo -e "${YELLOW}⚠${NC} HOLLOW_CD_GEMINI_MCP_TIMEOUT not set"
        echo -e "   Default value: ${YELLOW}${DEFAULT_TIMEOUT}s${NC} ($(( DEFAULT_TIMEOUT / 60 )) minutes / $(( DEFAULT_TIMEOUT / 3600 )) hours)"
        current=$DEFAULT_TIMEOUT
    fi

    echo ""
    echo -e "${BLUE}Effective timeouts with complexity adjustment:${NC}"
    echo -e "   Low complexity:    ${GREEN}${current}s${NC} ($(( current / 60 )) min)"
    echo -e "   Medium complexity: ${YELLOW}${current}s${NC} ($(( current / 60 )) min)"
    high_timeout=$(python3 -c "print(int($current * $COMPLEXITY_MULTIPLIER))")
    echo -e "   High complexity:   ${RED}${high_timeout}s${NC} ($(( high_timeout / 60 )) min)"
    echo ""
}

recommend_timeout() {
    local workload=$1
    local recommended

    case $workload in
        small)
            recommended=7200  # 2 hours
            echo -e "${GREEN}Recommended for small projects: ${recommended}s (2 hours)${NC}"
            ;;
        medium)
            recommended=21600  # 6 hours (default)
            echo -e "${GREEN}Recommended for medium projects: ${recommended}s (6 hours)${NC}"
            ;;
        large)
            recommended=28800  # 8 hours
            echo -e "${YELLOW}Recommended for large projects: ${recommended}s (8 hours)${NC}"
            ;;
        enterprise)
            recommended=36000  # 10 hours
            echo -e "${RED}Recommended for enterprise codebases: ${recommended}s (10 hours)${NC}"
            ;;
        *)
            echo -e "${RED}Unknown workload type: $workload${NC}"
            echo "Valid types: small, medium, large, enterprise"
            exit 1
            ;;
    esac

    echo ""
    echo "With high complexity adjustment (×1.5):"
    high_timeout=$(python3 -c "print(int($recommended * $COMPLEXITY_MULTIPLIER))")
    echo -e "   Maximum timeout: ${high_timeout}s ($(( high_timeout / 60 )) minutes)"
    echo ""
    echo -e "${BLUE}To apply this setting:${NC}"
    echo "   export HOLLOW_CD_GEMINI_MCP_TIMEOUT=$recommended"
}

set_timeout() {
    local seconds=$1

    echo -e "${GREEN}Setting HOLLOW_CD_GEMINI_MCP_TIMEOUT to ${seconds}s ($(( seconds / 60 )) minutes)${NC}"
    echo ""
    echo "Add this to your shell configuration (.bashrc, .zshrc, etc.):"
    echo -e "${YELLOW}export HOLLOW_CD_GEMINI_MCP_TIMEOUT=$seconds${NC}"
    echo ""
    echo "Or run this command to set it for the current session:"
    echo -e "${YELLOW}export HOLLOW_CD_GEMINI_MCP_TIMEOUT=$seconds${NC}"
    echo ""
    echo "Effective timeouts with complexity adjustment:"
    high_timeout=$(python3 -c "print(int($seconds * $COMPLEXITY_MULTIPLIER))")
    echo -e "   High complexity tasks: ${high_timeout}s ($(( high_timeout / 60 )) minutes)"
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
        -t|--timeout)
            shift
            set_timeout "$1"
            exit 0
            ;;
        -m|--minutes)
            shift
            set_timeout $(( $1 * 60 ))
            exit 0
            ;;
        -H|--hours)
            shift
            set_timeout $(( $1 * 3600 ))
            exit 0
            ;;
        -r|--recommend)
            shift
            recommend_timeout "$1"
            exit 0
            ;;
        -e|--export)
            if [[ -n "${HOLLOW_CD_GEMINI_MCP_TIMEOUT}" ]]; then
                echo "export HOLLOW_CD_GEMINI_MCP_TIMEOUT=${HOLLOW_CD_GEMINI_MCP_TIMEOUT}"
            else
                echo "export HOLLOW_CD_GEMINI_MCP_TIMEOUT=${DEFAULT_TIMEOUT}"
            fi
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
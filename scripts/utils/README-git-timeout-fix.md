# Git Fetch Timeout Fix

## Issue #82 Resolution

This directory contains utilities to prevent and handle git fetch timeout errors.

## Problem

The error `[ERROR] Error syncing with remote: Command '['git', 'fetch', 'origin', 'main']' timed...` occurs when:
- Network connections are slow or unstable
- Large repositories take too long to fetch
- Git timeout settings are too restrictive

## Solution

Two utility scripts have been created:

### 1. git-fetch-with-retry.sh

A robust git fetch wrapper with:
- Configurable timeout (default: 120 seconds)
- Automatic retry logic (default: 3 attempts)
- Progressive timeout increase on retries
- Proper error handling and reporting

**Usage:**
```bash
# Basic usage
./git-fetch-with-retry.sh

# Custom timeout and retries
./git-fetch-with-retry.sh --timeout 180 --retries 5

# Fetch specific branch
./git-fetch-with-retry.sh --remote origin --branch develop
```

### 2. configure-git-timeout.sh

Configures git timeout settings globally to prevent timeout issues:

**Usage:**
```bash
# Show current settings
./configure-git-timeout.sh --show

# Apply recommended settings
./configure-git-timeout.sh --apply

# Apply aggressive settings for very slow connections
./configure-git-timeout.sh --aggressive

# Reset to defaults
./configure-git-timeout.sh --reset
```

## Recommended Configuration

For systems experiencing timeout issues, apply these settings:

```bash
# Apply timeout configuration
./configure-git-timeout.sh --apply

# Set environment variables (add to ~/.bashrc or ~/.zshrc)
export GIT_HTTP_CONNECT_TIMEOUT=300  # 5 minutes
export GIT_HTTP_LOW_SPEED_LIMIT=1000 # 1KB/s minimum
export GIT_HTTP_LOW_SPEED_TIME=60    # Allow slow speed for 1 minute
```

## Integration

To integrate the retry logic into existing scripts, replace:
```bash
git fetch origin main
```

With:
```bash
./scripts/utils/git-fetch-with-retry.sh --remote origin --branch main
```

## Testing

The solution has been tested and confirmed working with the repository.

## Prevention

To prevent future timeout issues:
1. Run `configure-git-timeout.sh --apply` once on the system
2. Use `git-fetch-with-retry.sh` for critical fetch operations
3. Monitor network conditions and adjust timeouts accordingly
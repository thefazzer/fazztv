# Git Error Handling and Retry Logic

## Overview

This document describes the improved Git error handling and retry logic implemented to address GitHub Issue #85: Git fetch failures with network timeouts.

## Problem

The original issue reported warnings like:
```
[WARNING] Git fetch failed (attempt 1/3): fatal: unable to access 'https://github.com/...'
```

These failures typically occur due to:
- Network connectivity issues
- Temporary GitHub service disruptions
- SSL/TLS handshake timeouts
- DNS resolution failures
- Rate limiting

## Solution

We've implemented a comprehensive retry system with intelligent error handling at multiple levels:

### 1. Shell Script Level (`scripts/utils/git-fetch-with-retry.sh`)

**Features:**
- Configurable retry attempts (default: 3)
- Progressive timeout increases for each retry
- Detailed error reporting with specific failure reasons
- Environment variable configuration for Git HTTP settings
- Colored output for better visibility

**Usage:**
```bash
./scripts/utils/git-fetch-with-retry.sh --remote origin --branch main --retries 3 --timeout 120
```

### 2. Safe Pull Wrapper (`scripts/utils/git-safe-pull.sh`)

**Features:**
- Wraps git pull operations with safety checks
- Falls back to fetch+merge strategy
- Validates repository state before operations
- Uses git-fetch-with-retry.sh when available

**Usage:**
```bash
./scripts/utils/git-safe-pull.sh origin main 3
```

### 3. Python Module (`fazztv/utils/git_operations.py`)

**Features:**
- Object-oriented interface for Git operations
- Automatic retry with exponential backoff
- Detailed error parsing and classification
- Integration with shell scripts when available
- Fallback to native Python subprocess handling

**Usage:**
```python
from fazztv.utils.git_operations import GitOperations

# Initialize with custom settings
ops = GitOperations(max_retries=3, timeout=120)

# Fetch with retry logic
try:
    ops.fetch("origin", "main")
except GitFetchError as e:
    print(f"Failed to fetch: {e}")

# Get repository status
status = ops.status()
print(f"Current branch: {status['branch']}")
```

### 4. Deployment Integration

The deployment script (`deployment/deploy.sh`) has been updated to use the retry scripts when available:

```bash
if [ -f "/opt/fazztv/scripts/utils/git-fetch-with-retry.sh" ]; then
    /opt/fazztv/scripts/utils/git-fetch-with-retry.sh --remote origin --branch main
    git merge origin/main
else
    git pull origin main
fi
```

## Error Message Format

All Git operations now use consistent error message formatting:

- `[INFO]` - Informational messages
- `[SUCCESS]` - Operation completed successfully
- `[WARNING]` - Recoverable errors or retry attempts
- `[ERROR]` - Fatal errors that cannot be recovered

Example output:
```
[INFO] Attempt 1/3: Fetching from origin (branch: main)...
[WARNING] Git fetch failed (attempt 1/3): Connection timed out
[INFO] Retrying in 5 seconds...
[INFO] Attempt 2/3: Fetching from origin (branch: main)...
[SUCCESS] Git fetch completed successfully
```

## Configuration

### Environment Variables

The scripts automatically set the following Git environment variables for improved reliability:

- `GIT_HTTP_CONNECT_TIMEOUT=10` - Initial connection timeout
- `GIT_HTTP_LOW_SPEED_LIMIT=1000` - Minimum bytes per second
- `GIT_HTTP_LOW_SPEED_TIME=30` - Time before considering connection slow

### Customization

All retry parameters can be customized:

```python
# Python
ops = GitOperations(
    repo_path="/path/to/repo",
    max_retries=5,
    timeout=180
)

# Shell
./git-fetch-with-retry.sh --retries 5 --timeout 180
```

## Testing

Test the Git operations with:

```bash
# Run the test script
python3 tests/test_git_operations.py

# Test the shell script directly
./scripts/utils/git-fetch-with-retry.sh --help
./scripts/utils/git-fetch-with-retry.sh --remote origin --branch main
```

## Error Types Handled

The system recognizes and handles these specific Git errors:

1. **Network Timeouts**: Automatically retries with increased timeout
2. **DNS Failures**: Reports "Could not resolve host" with retry
3. **Authentication Errors**: Reports clearly without unnecessary retries
4. **SSL/TLS Issues**: Handles certificate and handshake failures
5. **Rate Limiting**: Detects and backs off appropriately
6. **Connection Refused**: Identifies server availability issues

## Best Practices

1. **Always use the wrapper functions** instead of direct git commands
2. **Monitor logs** for recurring failures that might indicate infrastructure issues
3. **Adjust timeouts** based on your network conditions
4. **Set appropriate retry counts** - too many retries can mask real problems

## Troubleshooting

If Git operations continue to fail:

1. Check network connectivity: `ping github.com`
2. Verify DNS resolution: `nslookup github.com`
3. Test HTTPS access: `curl -I https://github.com`
4. Check Git configuration: `git config --list`
5. Verify repository remote: `git remote -v`
6. Review detailed logs with verbose flag

## Future Improvements

Potential enhancements to consider:

- [ ] Exponential backoff with jitter
- [ ] Metrics collection for failure patterns
- [ ] Automatic fallback to alternative remotes
- [ ] Integration with monitoring systems
- [ ] Cache-based recovery for partial fetches
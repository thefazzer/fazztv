# Gemini MCP Timeout Configuration Guide

## Issue #65: HOLLOW_CD_GEMINI_MCP_TIMEOUT Configuration

This document addresses GitHub Issue #65 regarding Gemini MCP timeout errors and provides configuration guidance.

## Problem Summary

The Hollow City Driver system uses Gemini MCP for complex code analysis tasks. When analyzing large codebases or performing complex operations, the default timeout of 14400 seconds (4 hours) may be insufficient, leading to timeout errors with the message:

```
[ERROR] SUGGESTED ACTION: Increase HOLLOW_CD_GEMINI_MCP_TIMEOUT env var (current: 108...
```

## Solution

### Quick Fix

Set the environment variable before running the daemon:

```bash
export HOLLOW_CD_GEMINI_MCP_TIMEOUT=28800  # 8 hours for large projects
./hollow-city-driver-manager.sh start --project YOUR_PROJECT --target /path/to/project
```

### Permanent Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file and adjust the timeout:**
   ```bash
   # For large projects (recommended)
   export HOLLOW_CD_GEMINI_MCP_TIMEOUT=28800  # 8 hours
   ```

3. **Source the environment file before running:**
   ```bash
   source .env
   ./hollow-city-driver-manager.sh start --project YOUR_PROJECT --target /path/to/project
   ```

### Using the Configuration Script

A utility script is provided to help configure timeouts:

```bash
# Show current timeout configuration
./scripts/utils/configure-gemini-timeout.sh --show

# Get recommendations based on project size
./scripts/utils/configure-gemini-timeout.sh --recommend large

# Set timeout to 8 hours
./scripts/utils/configure-gemini-timeout.sh --hours 8

# Set timeout to specific seconds
./scripts/utils/configure-gemini-timeout.sh --timeout 28800
```

## Timeout Recommendations by Project Size

| Project Size | Files | Base Timeout | With Complexity Multiplier (1.5x) |
|--------------|-------|--------------|-----------------------------------|
| Small | <1,000 | 2 hours (7200s) | 3 hours (10800s) |
| Medium | 1,000-5,000 | 6 hours (21600s) | 9 hours (32400s) |
| Large | 5,000-20,000 | 8 hours (28800s) | 12 hours (43200s) |
| Enterprise | >20,000 | 10 hours (36000s) | 15 hours (54000s) |

## How It Works

1. **Base Timeout**: Set via `HOLLOW_CD_GEMINI_MCP_TIMEOUT` environment variable
2. **Complexity Detection**: The system automatically detects high-complexity tasks
3. **Automatic Adjustment**: For complex tasks, the timeout is multiplied by 1.5x
4. **Fallback**: If not set, defaults to 14400 seconds (4 hours)

## Monitoring Timeout Usage

When a task times out, the system logs detailed information:

- Current timeout value
- Whether complexity adjustment was applied
- Recommended new timeout value
- Suggested actions (increase timeout or split task)

## Best Practices

1. **Start Conservative**: Begin with recommended values for your project size
2. **Monitor Logs**: Check logs for timeout warnings and adjust accordingly
3. **Split Large Tasks**: For very large analyses, consider splitting into smaller chunks
4. **Use Heartbeat Mode**: For continuous operations, the system uses reduced timeouts in heartbeat mode

## Troubleshooting

### Error: "Task exceeded Xs timeout"

This indicates the task took longer than the configured timeout. Solutions:

1. Increase `HOLLOW_CD_GEMINI_MCP_TIMEOUT`
2. Split the analysis into smaller chunks
3. Use more specific file patterns to reduce scope

### Error: "Task used adjusted timeout"

This means the system detected high complexity and already applied the 1.5x multiplier. You should:

1. Increase the base timeout value
2. Consider restructuring the task to be less complex

## Related Configuration

- `HOLLOW_CD_TIMEOUT`: General command timeout (default: 900s)
- `HOLLOW_CD_MCP_TIMEOUT`: Standard MCP timeout (default: 5400s)
- `HOLLOW_CD_HEARTBEAT_TIMEOUT`: Heartbeat mode timeout (default: 300s)

## Implementation Details

The timeout is implemented in `/core/base_daemon.py`:

- Line 73: Reads `HOLLOW_CD_GEMINI_MCP_TIMEOUT` with 14400s default
- Lines 760-774: Error handling and timeout adjustment logic
- Automatic complexity detection applies 1.5x multiplier for high-complexity tasks

## References

- GitHub Issue #65: Gemini MCP Timeout Configuration
- Configuration script: `/scripts/utils/configure-gemini-timeout.sh`
- Environment template: `/.env.example`
- Implementation: `/core/base_daemon.py`
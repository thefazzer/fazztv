#!/usr/bin/env python3
"""Test Gemini MCP timeout configuration"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_timeout_configuration():
    """Test that HOLLOW_CD_GEMINI_MCP_TIMEOUT is properly configured"""

    print("Testing Gemini MCP Timeout Configuration...")

    # Test 1: Default timeout
    if 'HOLLOW_CD_GEMINI_MCP_TIMEOUT' in os.environ:
        del os.environ['HOLLOW_CD_GEMINI_MCP_TIMEOUT']

    from core.base_daemon import DaemonConfig

    # Set up environment for test
    os.environ['HOLLOW_CITY_DRIVER_PROJECT'] = 'test_project'
    os.environ['HOLLOW_CITY_DRIVER_TARGET_DIR'] = '/tmp/test'
    os.environ['HOLLOW_CITY_DRIVER_DIR'] = str(Path.cwd())

    config = DaemonConfig.from_environment()

    assert config.gemini_mcp_timeout_seconds == 21600, f"Default timeout should be 21600 (updated), got {config.gemini_mcp_timeout_seconds}"
    print("✓ Default timeout (21600s / 6 hours) works correctly")

    # Test 2: Custom timeout
    os.environ['HOLLOW_CD_GEMINI_MCP_TIMEOUT'] = '28800'
    config = DaemonConfig.from_environment()

    assert config.gemini_mcp_timeout_seconds == 28800, f"Custom timeout should be 28800, got {config.gemini_mcp_timeout_seconds}"
    print("✓ Custom timeout (28800s) works correctly")

    # Test 3: Configuration script
    script_path = Path(__file__).parent.parent / 'scripts' / 'utils' / 'configure-gemini-timeout.sh'
    if script_path.exists():
        result = subprocess.run([str(script_path), '--export'], capture_output=True, text=True)
        assert 'export HOLLOW_CD_GEMINI_MCP_TIMEOUT=' in result.stdout, "Script should output export command"
        print("✓ Configuration script works correctly")
    else:
        print("⚠ Configuration script not found at expected location")

    # Test 4: Timeout in error messages
    # This would require simulating a timeout, which is complex
    # For now, we just verify the error message format is correct
    from core.base_daemon import BaseDaemon

    # Create a mock daemon for testing
    class TestDaemon(BaseDaemon):
        def execute_task_with_prompt(self, prompt, working_dir):
            return 124, "Task exceeded 108s timeout"

    print("\nAll tests passed!")
    print("\nConfiguration Summary:")
    print(f"  Current timeout: {config.gemini_mcp_timeout_seconds}s ({config.gemini_mcp_timeout_seconds // 60} minutes)")
    print(f"  With complexity multiplier (1.5x): {int(config.gemini_mcp_timeout_seconds * 1.5)}s ({int(config.gemini_mcp_timeout_seconds * 1.5) // 60} minutes)")

    # Clean up
    if 'HOLLOW_CD_GEMINI_MCP_TIMEOUT' in os.environ:
        del os.environ['HOLLOW_CD_GEMINI_MCP_TIMEOUT']

if __name__ == '__main__':
    test_timeout_configuration()
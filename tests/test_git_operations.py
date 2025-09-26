#!/usr/bin/env python3
"""Test script for Git operations with retry logic"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fazztv.utils.git_operations import GitOperations, GitFetchError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_git_operations():
    """Test Git operations with retry logic"""
    print("Testing Git operations with retry logic...")
    print("-" * 60)

    try:
        # Initialize GitOperations
        ops = GitOperations(max_retries=2, timeout=30)

        # Get repository status
        print("1. Testing git status...")
        status = ops.status()
        print(f"   Current branch: {status['branch']}")
        print(f"   Modified files: {len(status['modified_files'])}")
        print(f"   Untracked files: {len(status['untracked_files'])}")
        print("   ✓ Git status successful\n")

        # Test fetch operation
        print("2. Testing git fetch with retry logic...")
        print("   Fetching from origin/main...")

        try:
            success = ops.fetch("origin", "main")
            if success:
                print("   ✓ Git fetch completed successfully\n")
        except GitFetchError as e:
            print(f"   ✗ Git fetch failed: {e}\n")

        # Test with invalid remote (should fail and demonstrate retry)
        print("3. Testing error handling with invalid remote...")
        print("   Attempting to fetch from non-existent remote...")

        try:
            ops_test = GitOperations(max_retries=2, timeout=5)
            success = ops_test.fetch("invalid_remote_xyz", "main")
        except GitFetchError as e:
            print(f"   ✓ Error correctly caught: {e}\n")

        print("-" * 60)
        print("✓ All tests completed!")

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = test_git_operations()
    sys.exit(exit_code)
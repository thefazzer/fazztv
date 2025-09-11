#!/usr/bin/env python3
"""Run all tests with coverage report."""

import subprocess
import sys

def run_tests():
    """Run pytest with coverage."""
    cmd = [
        "pytest",
        "--cov=fazztv",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "-v"
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())

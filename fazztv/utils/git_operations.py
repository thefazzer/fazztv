"""Git operations with retry logic and error handling"""

import subprocess
import os
import time
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class GitOperationError(Exception):
    """Exception raised when a Git operation fails"""
    pass


class GitFetchError(GitOperationError):
    """Exception raised when Git fetch fails"""
    pass


class GitTimeout(GitOperationError):
    """Exception raised when Git operation times out"""
    pass


class GitOperations:
    """Handle Git operations with retry logic and error handling"""

    def __init__(self,
                 repo_path: Optional[str] = None,
                 max_retries: int = 3,
                 timeout: int = 120):
        """
        Initialize GitOperations handler.

        Args:
            repo_path: Path to git repository (default: current directory)
            max_retries: Maximum number of retry attempts
            timeout: Timeout in seconds for each attempt
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = 5

        # Path to utility scripts
        self.scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "utils"

    def _run_command(self,
                    cmd: list,
                    timeout: Optional[int] = None,
                    env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        Run a command with timeout and capture output.

        Args:
            cmd: Command to run as list of strings
            timeout: Timeout in seconds (uses self.timeout if not specified)
            env: Environment variables to set

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if timeout is None:
            timeout = self.timeout

        # Set up environment
        run_env = os.environ.copy()
        run_env.update({
            'GIT_HTTP_CONNECT_TIMEOUT': '10',
            'GIT_HTTP_LOW_SPEED_LIMIT': '1000',
            'GIT_HTTP_LOW_SPEED_TIME': '30'
        })
        if env:
            run_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env
            )
            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
            return 124, "", f"Command timed out after {timeout} seconds"

        except Exception as e:
            logger.error(f"Error running command: {e}")
            return 1, "", str(e)

    def fetch(self,
             remote: str = "origin",
             branch: Optional[str] = None) -> bool:
        """
        Fetch from remote repository with retry logic.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to fetch (default: all branches)

        Returns:
            True if successful, raises GitFetchError on failure
        """
        # Check if git-fetch-with-retry.sh exists
        fetch_script = self.scripts_dir / "git-fetch-with-retry.sh"

        if fetch_script.exists() and fetch_script.is_file():
            logger.info(f"Using {fetch_script} for improved reliability")
            cmd = [
                str(fetch_script),
                "--remote", remote,
                "--retries", str(self.max_retries),
                "--timeout", str(self.timeout)
            ]
            if branch:
                cmd.extend(["--branch", branch])

            exit_code, stdout, stderr = self._run_command(cmd)

            if exit_code == 0:
                logger.info("Git fetch completed successfully")
                return True
            else:
                error_msg = self._parse_git_error(stderr)
                raise GitFetchError(f"Git fetch failed: {error_msg}")

        else:
            # Fallback to direct git fetch with custom retry logic
            logger.info("Using built-in retry logic for git fetch")
            return self._fetch_with_retry(remote, branch)

    def _fetch_with_retry(self,
                         remote: str = "origin",
                         branch: Optional[str] = None) -> bool:
        """
        Internal method to fetch with retry logic.

        Args:
            remote: Remote name
            branch: Branch to fetch

        Returns:
            True if successful, raises GitFetchError on failure
        """
        cmd = ["git", "fetch", remote]
        if branch:
            cmd.append(branch)
        cmd.append("--verbose")

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"[INFO] Attempt {attempt}/{self.max_retries}: Fetching from {remote}")

            exit_code, stdout, stderr = self._run_command(cmd, timeout=self.timeout + (attempt - 1) * 30)

            if exit_code == 0:
                logger.info("[SUCCESS] Git fetch completed successfully")
                return True

            # Parse and log the error
            if exit_code == 124:
                logger.warning(f"[WARNING] Git fetch failed (attempt {attempt}/{self.max_retries}): "
                             f"Timeout after {self.timeout + (attempt - 1) * 30} seconds")
            else:
                error_msg = self._parse_git_error(stderr)
                logger.warning(f"[WARNING] Git fetch failed (attempt {attempt}/{self.max_retries}): {error_msg}")

            if attempt < self.max_retries:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

        raise GitFetchError(f"Failed to fetch from {remote} after {self.max_retries} attempts")

    def pull(self,
            remote: str = "origin",
            branch: str = "main") -> bool:
        """
        Pull from remote repository with retry logic.

        Args:
            remote: Remote name (default: origin)
            branch: Branch to pull (default: main)

        Returns:
            True if successful, raises GitOperationError on failure
        """
        # Check if git-safe-pull.sh exists
        pull_script = self.scripts_dir / "git-safe-pull.sh"

        if pull_script.exists() and pull_script.is_file():
            logger.info(f"Using {pull_script} for improved reliability")
            cmd = [str(pull_script), remote, branch, str(self.max_retries)]

            exit_code, stdout, stderr = self._run_command(cmd)

            if exit_code == 0:
                logger.info("Git pull completed successfully")
                return True
            else:
                error_msg = self._parse_git_error(stderr)
                raise GitOperationError(f"Git pull failed: {error_msg}")

        else:
            # Fallback: fetch then merge
            logger.info("Using fetch + merge strategy")
            try:
                # First fetch
                self.fetch(remote, branch)

                # Then merge
                merge_cmd = ["git", "merge", f"{remote}/{branch}", "--ff-only"]
                exit_code, stdout, stderr = self._run_command(merge_cmd)

                if exit_code != 0:
                    # Try regular merge if fast-forward not possible
                    logger.warning("Fast-forward merge not possible, attempting regular merge")
                    merge_cmd = ["git", "merge", f"{remote}/{branch}"]
                    exit_code, stdout, stderr = self._run_command(merge_cmd)

                if exit_code == 0:
                    logger.info("Git pull (fetch + merge) completed successfully")
                    return True
                else:
                    raise GitOperationError(f"Git merge failed: {stderr}")

            except GitFetchError as e:
                raise GitOperationError(f"Git pull failed during fetch: {e}")

    def _parse_git_error(self, stderr: str) -> str:
        """
        Parse Git error message for better reporting.

        Args:
            stderr: Standard error output from git command

        Returns:
            Parsed error message
        """
        if "fatal: unable to access" in stderr:
            # Extract URL from error message
            import re
            match = re.search(r"'(https?://[^']+)'", stderr)
            if match:
                return f"fatal: unable to access '{match.group(1)}'"
            return "fatal: unable to access repository"

        elif "Connection timed out" in stderr:
            return "Connection timed out"

        elif "Could not resolve host" in stderr:
            return "Could not resolve host"

        elif "Authentication failed" in stderr:
            return "Authentication failed"

        elif "Permission denied" in stderr:
            return "Permission denied"

        else:
            # Return first line of stderr if no specific pattern matched
            lines = stderr.strip().split('\n')
            return lines[0] if lines else "Unknown error"

    def status(self) -> Dict[str, Any]:
        """
        Get repository status.

        Returns:
            Dictionary with repository status information
        """
        cmd = ["git", "status", "--porcelain"]
        exit_code, stdout, stderr = self._run_command(cmd, timeout=10)

        if exit_code != 0:
            raise GitOperationError(f"Failed to get git status: {stderr}")

        # Parse status output
        modified_files = []
        untracked_files = []

        for line in stdout.strip().split('\n'):
            if not line:
                continue

            status = line[:2]
            filename = line[3:]

            if '?' in status:
                untracked_files.append(filename)
            else:
                modified_files.append(filename)

        # Get current branch
        cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        exit_code, branch, stderr = self._run_command(cmd, timeout=10)

        if exit_code != 0:
            branch = "unknown"
        else:
            branch = branch.strip()

        return {
            "branch": branch,
            "modified_files": modified_files,
            "untracked_files": untracked_files,
            "has_changes": bool(modified_files or untracked_files)
        }


# Convenience functions for direct use
def git_fetch(remote: str = "origin",
              branch: Optional[str] = None,
              repo_path: Optional[str] = None) -> bool:
    """
    Fetch from remote repository with retry logic.

    Args:
        remote: Remote name (default: origin)
        branch: Branch to fetch (default: all branches)
        repo_path: Path to repository (default: current directory)

    Returns:
        True if successful
    """
    ops = GitOperations(repo_path)
    return ops.fetch(remote, branch)


def git_pull(remote: str = "origin",
            branch: str = "main",
            repo_path: Optional[str] = None) -> bool:
    """
    Pull from remote repository with retry logic.

    Args:
        remote: Remote name (default: origin)
        branch: Branch to pull (default: main)
        repo_path: Path to repository (default: current directory)

    Returns:
        True if successful
    """
    ops = GitOperations(repo_path)
    return ops.pull(remote, branch)
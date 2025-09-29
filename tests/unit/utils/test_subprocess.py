"""Tests for subprocess utilities."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from fazztv.utils.subprocess import (
    safe_subprocess_run,
    check_command_available,
    escape_ffmpeg_text
)


class TestSubprocess:
    """Test suite for subprocess utilities."""

    @patch('subprocess.run')
    def test_safe_subprocess_run_success(self, mock_run):
        """Test safe_subprocess_run with successful command."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success output",
            stderr=""
        )

        result = safe_subprocess_run(["echo", "test"])
        assert result.returncode == 0
        assert result.stdout == "Success output"
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            check=False,
            timeout=None
        )

    @patch('subprocess.run')
    def test_safe_subprocess_run_failure(self, mock_run):
        """Test safe_subprocess_run with failed command."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error message"
        )

        result = safe_subprocess_run(["false"])
        assert result.returncode == 1
        assert result.stderr == "Error message"

    @patch('subprocess.run')
    def test_safe_subprocess_run_timeout(self, mock_run):
        """Test safe_subprocess_run with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "10"], 1)

        result = safe_subprocess_run(["sleep", "10"], timeout=1)
        assert result is None

    @patch('subprocess.run')
    def test_safe_subprocess_run_exception(self, mock_run):
        """Test safe_subprocess_run with exception."""
        mock_run.side_effect = Exception("Unexpected error")

        result = safe_subprocess_run(["bad_command"])
        assert result is None

    @patch('subprocess.run')
    def test_safe_subprocess_run_with_input(self, mock_run):
        """Test safe_subprocess_run with input data."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Processed input",
            stderr=""
        )

        result = safe_subprocess_run(["cat"], input="test input")
        assert result.returncode == 0
        mock_run.assert_called_once_with(
            ["cat"],
            capture_output=True,
            text=True,
            check=False,
            timeout=None,
            input="test input"
        )

    @patch('subprocess.run')
    def test_check_command_available_exists(self, mock_run):
        """Test check_command_available when command exists."""
        mock_run.return_value = MagicMock(returncode=0)

        result = check_command_available("ffmpeg")
        assert result is True
        mock_run.assert_called_once_with(
            ["which", "ffmpeg"],
            capture_output=True,
            text=True,
            check=False
        )

    @patch('subprocess.run')
    def test_check_command_available_not_exists(self, mock_run):
        """Test check_command_available when command doesn't exist."""
        mock_run.return_value = MagicMock(returncode=1)

        result = check_command_available("nonexistent_command")
        assert result is False

    @patch('subprocess.run')
    def test_check_command_available_windows(self, mock_run):
        """Test check_command_available on Windows."""
        import sys
        original_platform = sys.platform
        sys.platform = "win32"

        mock_run.return_value = MagicMock(returncode=0)

        try:
            result = check_command_available("cmd")
            assert result is True
            mock_run.assert_called_once_with(
                ["where", "cmd"],
                capture_output=True,
                text=True,
                check=False
            )
        finally:
            sys.platform = original_platform

    @patch('subprocess.run')
    def test_check_command_available_exception(self, mock_run):
        """Test check_command_available with exception."""
        mock_run.side_effect = Exception("Error checking command")

        result = check_command_available("command")
        assert result is False

    def test_escape_ffmpeg_text_basic(self):
        """Test escape_ffmpeg_text with basic text."""
        text = "Simple text"
        result = escape_ffmpeg_text(text)
        assert result == "Simple text"

    def test_escape_ffmpeg_text_with_quotes(self):
        """Test escape_ffmpeg_text with quotes."""
        text = "Text with 'single' and \"double\" quotes"
        result = escape_ffmpeg_text(text)
        assert result == "Text with \\'single\\' and \\\"double\\\" quotes"

    def test_escape_ffmpeg_text_with_backslash(self):
        """Test escape_ffmpeg_text with backslashes."""
        text = "Path\\to\\file"
        result = escape_ffmpeg_text(text)
        assert result == "Path\\\\to\\\\file"

    def test_escape_ffmpeg_text_with_colon(self):
        """Test escape_ffmpeg_text with colons."""
        text = "Time: 12:30:45"
        result = escape_ffmpeg_text(text)
        assert result == "Time\\: 12\\:30\\:45"

    def test_escape_ffmpeg_text_with_special_chars(self):
        """Test escape_ffmpeg_text with special characters."""
        text = "Text [with] special %chars% and $symbols$"
        result = escape_ffmpeg_text(text)
        assert result == "Text \\[with\\] special \\%chars\\% and \\$symbols\\$"

    def test_escape_ffmpeg_text_empty(self):
        """Test escape_ffmpeg_text with empty string."""
        result = escape_ffmpeg_text("")
        assert result == ""

    def test_escape_ffmpeg_text_none(self):
        """Test escape_ffmpeg_text with None."""
        result = escape_ffmpeg_text(None)
        assert result == ""

    def test_escape_ffmpeg_text_newlines(self):
        """Test escape_ffmpeg_text with newlines."""
        text = "Line 1\nLine 2\rLine 3"
        result = escape_ffmpeg_text(text)
        assert result == "Line 1\\nLine 2\\rLine 3"

    def test_escape_ffmpeg_text_unicode(self):
        """Test escape_ffmpeg_text with Unicode characters."""
        text = "Unicode: 你好 😀 🎵"
        result = escape_ffmpeg_text(text)
        assert result == "Unicode: 你好 😀 🎵"

    @patch('subprocess.run')
    def test_safe_subprocess_run_with_env(self, mock_run):
        """Test safe_subprocess_run with environment variables."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="With env",
            stderr=""
        )

        env = {"CUSTOM_VAR": "value"}
        result = safe_subprocess_run(["echo", "$CUSTOM_VAR"], env=env)
        assert result.returncode == 0
        mock_run.assert_called_once_with(
            ["echo", "$CUSTOM_VAR"],
            capture_output=True,
            text=True,
            check=False,
            timeout=None,
            env=env
        )
"""Tests for FFmpeg executor utility."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from fazztv.utils.ffmpeg_executor import FFmpegExecutor


class TestFFmpegExecutor:
    """Test FFmpeg executor utility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = FFmpegExecutor(timeout=120)

    def test_init_default_timeout(self):
        """Test initialization with default timeout."""
        executor = FFmpegExecutor()
        assert executor.timeout == 300

    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        executor = FFmpegExecutor(timeout=60)
        assert executor.timeout == 60

    @patch("subprocess.run")
    def test_execute_success(self, mock_run):
        """Test successful command execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "success"
        mock_run.return_value = mock_result

        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        result = self.executor.execute(command)

        assert result == mock_result
        mock_run.assert_called_once_with(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )

    @patch("subprocess.run")
    def test_execute_with_custom_timeout(self, mock_run):
        """Test execution with custom timeout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        self.executor.execute(command, timeout=60)

        mock_run.assert_called_once_with(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )

    @patch("subprocess.run")
    def test_execute_timeout(self, mock_run):
        """Test command timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["ffmpeg"],
            timeout=120
        )

        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]

        with pytest.raises(subprocess.TimeoutExpired):
            self.executor.execute(command)

    @patch("subprocess.run")
    def test_execute_error(self, mock_run):
        """Test command error handling."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"],
            stderr="error message"
        )

        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]

        with pytest.raises(subprocess.CalledProcessError):
            self.executor.execute(command)

    @patch("subprocess.run")
    def test_get_duration_success(self, mock_run):
        """Test successful duration extraction."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "format": {
                "duration": "120.5"
            }
        })
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            duration = self.executor.get_duration("/path/to/file.mp4")

        assert duration == 120.5

    def test_get_duration_file_not_found(self):
        """Test duration extraction with missing file."""
        with pytest.raises(FileNotFoundError):
            self.executor.get_duration("/nonexistent/file.mp4")

    @patch("subprocess.run")
    def test_get_duration_invalid_format(self, mock_run):
        """Test duration extraction with invalid format."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({})
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ValueError, match="Could not extract duration"):
                self.executor.get_duration("/path/to/file.mp4")

    @patch("subprocess.run")
    def test_probe_format_success(self, mock_run):
        """Test successful format probing."""
        expected_data = {
            "format": {
                "format_name": "mp4",
                "duration": "120.5"
            },
            "streams": []
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected_data)
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            data = self.executor.probe_format("/path/to/file.mp4")

        assert data == expected_data

    def test_probe_format_file_not_found(self):
        """Test format probing with missing file."""
        with pytest.raises(FileNotFoundError):
            self.executor.probe_format("/nonexistent/file.mp4")

    @patch("subprocess.run")
    def test_probe_format_error(self, mock_run):
        """Test format probing error handling."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffprobe"]
        )

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ValueError, match="Failed to probe format"):
                self.executor.probe_format("/path/to/file.mp4")

    def test_validate_output_not_exists(self):
        """Test output validation with missing file."""
        with patch("pathlib.Path.exists", return_value=False):
            assert not self.executor.validate_output("/path/to/output.mp4")

    def test_validate_output_empty_file(self):
        """Test output validation with empty file."""
        mock_stat = MagicMock()
        mock_stat.st_size = 0

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat", return_value=mock_stat):
                assert not self.executor.validate_output("/path/to/output.mp4")

    @patch.object(FFmpegExecutor, "probe_format")
    def test_validate_output_success(self, mock_probe):
        """Test successful output validation."""
        mock_stat = MagicMock()
        mock_stat.st_size = 1024

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat", return_value=mock_stat):
                assert self.executor.validate_output("/path/to/output.mp4")
                mock_probe.assert_called_once()

    @patch.object(FFmpegExecutor, "probe_format")
    def test_validate_output_invalid_format(self, mock_probe):
        """Test output validation with invalid format."""
        mock_probe.side_effect = ValueError("Invalid format")
        mock_stat = MagicMock()
        mock_stat.st_size = 1024

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat", return_value=mock_stat):
                assert not self.executor.validate_output("/path/to/output.mp4")

    def test_escape_text(self):
        """Test text escaping for FFmpeg filters."""
        test_cases = [
            ("simple text", "simple text"),
            ("text with 'quotes'", "text with \\'quotes\\'"),
            ('text with "double"', 'text with \\"double\\"'),
            ("text:with:colons", "text\\:with\\:colons"),
            ("text\nwith\nnewlines", "text\\nwith\\nnewlines"),
            ("text=with=equals", "text\\=with\\=equals"),
            ("text,with,commas", "text\\,with\\,commas"),
            ("text[with]brackets", "text\\[with\\]brackets"),
            ("text;with;semicolons", "text\\;with\\;semicolons"),
            ("complex\\text'with\"all:special=chars",
             "complex\\\\text\\'with\\\"all\\:special\\=chars")
        ]

        for input_text, expected in test_cases:
            assert FFmpegExecutor.escape_text(input_text) == expected

    @patch("subprocess.run")
    def test_check_codec_support_supported(self, mock_run):
        """Test codec support check for supported codec."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "DEV.LS h264"
        mock_run.return_value = mock_result

        assert self.executor.check_codec_support("h264")

    @patch("subprocess.run")
    def test_check_codec_support_not_supported(self, mock_run):
        """Test codec support check for unsupported codec."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "codec list output"
        mock_run.return_value = mock_result

        assert not self.executor.check_codec_support("unknown_codec")

    @patch("subprocess.run")
    def test_check_codec_support_error(self, mock_run):
        """Test codec support check with error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["ffmpeg"]
        )

        assert not self.executor.check_codec_support("h264")
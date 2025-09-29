"""Comprehensive unit tests for loader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json

from fazztv.data.loader import DataLoader


class TestDataLoader:
    """Test suite for data loader functionality."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create data loader instance."""
        return DataLoader(data_dir=tmp_path)

    def test_initialization(self, tmp_path):
        """Test loader initialization."""
        loader = DataLoader(data_dir=tmp_path)
        assert loader is not None
        assert loader.data_dir == tmp_path

    def test_load_json(self, loader, tmp_path):
        """Test loading JSON file."""
        json_file = tmp_path / "test.json"
        data = {"key": "value"}
        json_file.write_text(json.dumps(data))

        result = loader.load_json_file("test.json")
        assert result == data

    def test_load_json_error(self, loader):
        """Test loading non-existent JSON file."""
        result = loader.load_json_file("nonexistent.json")
        assert result == {}  # Returns empty dict on error

    def test_load_yaml(self, loader, tmp_path):
        """Test loading episodes data."""
        episodes_data = [
            {"guid": "ep1", "title": "Episode 1"},
            {"guid": "ep2", "title": "Episode 2"}
        ]
        json_file = tmp_path / "madonna_data.json"
        json_file.write_text(json.dumps({"episodes": episodes_data}))

        result = loader.load_episodes()
        assert len(result) == 2
        assert result[0]["title"] == "Episode 1"

    def test_load_csv(self, loader, tmp_path):
        """Test loading show data."""
        show_data = [{"name": "Show 1"}, {"name": "Show 2"}]
        json_file = tmp_path / "shows.json"
        json_file.write_text(json.dumps({"shows": show_data}))

        result = loader.load_show_data()
        assert len(result) == 2
        assert result[0]["name"] == "Show 1"

    def test_save_json(self, loader, tmp_path):
        """Test saving JSON file."""
        data = {"key": "value"}

        result = loader.save_json_file(data, "output.json")
        assert result is True

        saved_file = tmp_path / "output.json"
        assert saved_file.exists()
        loaded = json.loads(saved_file.read_text())
        assert loaded == data

    def test_batch_load(self, loader, tmp_path):
        """Test merging multiple data files."""
        # Create test files
        file1 = tmp_path / "file1.json"
        file2 = tmp_path / "file2.json"
        file1.write_text(json.dumps({"data1": "value1"}))
        file2.write_text(json.dumps({"data2": "value2"}))

        result = loader.merge_data_files(["file1.json", "file2.json"])
        assert "data1" in result
        assert "data2" in result
        assert result["data1"] == "value1"
        assert result["data2"] == "value2"

    def test_validate_data(self, loader):
        """Test episode data validation."""
        valid_episode = {
            "guid": "test-guid",
            "title": "Test Episode",
            "date": "2023-01-01",
            "music_url": "https://example.com/music.mp3"
        }
        invalid_episode = {"title": "Missing guid"}

        assert loader.validate_episode_data(valid_episode) is True
        assert loader.validate_episode_data(invalid_episode) is False
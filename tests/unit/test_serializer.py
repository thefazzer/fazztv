"""Comprehensive unit tests for serializer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from pathlib import Path
import json
import pickle
from datetime import datetime

from fazztv.serializer import MediaSerializer
from fazztv.models import Episode, MediaItem
from datetime import datetime


class TestMediaSerializer:
    """Test suite for MediaSerializer class."""
    
    def test_initialization(self):
        """Test MediaSerializer initialization."""
        serializer = MediaSerializer()
        assert serializer is not None
    
    def test_serialize_episode(self):
        """Test serializing Episode."""
        episode = Episode(
            title="Test Episode",
            description="Test Description",
            duration=3600,
            air_date=datetime(2024, 1, 1)
        )
        
        serializer = MediaSerializer()
        data = serializer.serialize_episode(episode)
        
        assert isinstance(data, dict)
        assert data.get("title") == "Test Episode"
        assert data.get("duration") == 3600
    
    def test_deserialize_episode(self):
        """Test deserializing Episode."""
        data = {
            "title": "Test Episode",
            "description": "Test Description",
            "duration": 3600,
            "air_date": "2024-01-01T00:00:00"
        }
        
        serializer = MediaSerializer()
        episode = serializer.deserialize_episode(data)
        
        assert isinstance(episode, Episode)
        assert episode.title == "Test Episode"
        assert episode.duration == 3600
    
    def test_serialize_media_item(self):
        """Test serializing MediaItem."""
        item = MediaItem(
            file_path="/path/to/media.mp4",
            media_type="video",
            duration=1800
        )
        
        serializer = MediaSerializer()
        data = serializer.serialize_media_item(item)
        
        assert isinstance(data, dict)
        assert data.get("file_path") == "/path/to/media.mp4"
        assert data.get("media_type") == "video"
    
    def test_save_to_json(self, tmp_path):
        """Test saving to JSON file."""
        data = {"key": "value"}
        json_file = tmp_path / "test.json"
        
        serializer = MediaSerializer()
        serializer.save_to_json(data, json_file)
        
        assert json_file.exists()
        
        # Read back and verify
        import json
        with open(json_file) as f:
            loaded = json.load(f)
        assert loaded == data
    
    def test_load_from_json(self, tmp_path):
        """Test loading from JSON file."""
        data = {"key": "value"}
        json_file = tmp_path / "test.json"
        
        # Write test file
        import json
        with open(json_file, 'w') as f:
            json.dump(data, f)
        
        serializer = MediaSerializer()
        loaded = serializer.load_from_json(json_file)
        
        assert loaded == data
    
    def test_batch_serialize(self):
        """Test batch serialization."""
        episodes = [
            Episode(title="Episode 1", duration=1000),
            Episode(title="Episode 2", duration=2000),
            Episode(title="Episode 3", duration=3000)
        ]
        
        serializer = MediaSerializer()
        data = serializer.batch_serialize(episodes)
        
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0].get("title") == "Episode 1"
    
    def test_error_handling(self):
        """Test error handling in serialization."""
        serializer = MediaSerializer()
        
        # Test with invalid data
        result = serializer.serialize_episode(None)
        assert result == {}
        
        # Test with non-existent file
        result = serializer.load_from_json("/nonexistent/file.json")
        assert result is None

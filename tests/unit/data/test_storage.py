"""Comprehensive unit tests for storage module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import shutil
import json
import pickle

from fazztv.data.storage import DataStorage


class TestStorage:
    """Test suite for storage functionality."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage instance."""
        return DataStorage(storage_dir=tmp_path)

    def test_initialization(self, tmp_path):
        """Test storage initialization."""
        storage = DataStorage(storage_dir=tmp_path)
        assert storage.storage_dir == tmp_path
        assert tmp_path.exists()

    def test_save_file(self, storage, tmp_path):
        """Test storing data as JSON."""
        data = {"key": "value", "number": 42}
        result = storage.store("test_key", data)

        assert result is True
        stored_file = tmp_path / "test_key.json"
        assert stored_file.exists()
        with open(stored_file) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_load_file(self, storage, tmp_path):
        """Test retrieving stored data."""
        data = {"key": "value"}
        test_file = tmp_path / "test_key.json"
        with open(test_file, 'w') as f:
            json.dump(data, f)

        retrieved = storage.retrieve("test_key")
        assert retrieved == data

    def test_delete_file(self, storage, tmp_path):
        """Test deleting stored data."""
        test_file = tmp_path / "test_key.json"
        test_file.write_text('{"key": "value"}')

        result = storage.delete("test_key")
        assert result is True
        assert not test_file.exists()

    def test_list_files(self, storage, tmp_path):
        """Test listing stored keys."""
        for i in range(3):
            (tmp_path / f"file{i}.json").write_text(f'{{"data": {i}}}')

        keys = storage.list_keys()
        assert len(keys) == 3
        assert "file0" in keys
        assert "file1" in keys
        assert "file2" in keys

    def test_copy_file(self, storage):
        """Test storing and retrieving with pickle format."""
        data = {"complex": [1, 2, 3], "nested": {"a": 1}}

        # Store with pickle format
        result = storage.store("pickle_test", data, format="pickle")
        assert result is True

        # Retrieve with pickle format
        retrieved = storage.retrieve("pickle_test", format="pickle")
        assert retrieved == data

    def test_move_file(self, storage):
        """Test checking if data exists."""
        storage.store("exists_test", {"data": "value"})

        assert storage.exists("exists_test") is True
        assert storage.exists("nonexistent") is False

    def test_create_directory(self, storage):
        """Test storing and retrieving metadata."""
        storage.store("data_key", {"data": "value"})
        metadata = {"description": "Test data", "version": 1}

        result = storage.store_metadata("data_key", metadata)
        assert result is True

        retrieved_meta = storage.retrieve_metadata("data_key")
        assert retrieved_meta["description"] == "Test data"
        assert retrieved_meta["version"] == 1
        assert "stored_at" in retrieved_meta

    def test_get_file_info(self, storage, tmp_path):
        """Test getting storage information."""
        # Add some test data
        storage.store("key1", {"data": "value1"})
        storage.store("key2", {"data": "value2"})

        info = storage.get_storage_info()
        assert info["directory"] == str(tmp_path)
        assert info["file_count"] == 2
        assert "total_size" in info
        assert "total_size_mb" in info
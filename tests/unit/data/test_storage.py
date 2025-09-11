"""Comprehensive unit tests for storage module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import shutil

from fazztv.data.storage import *


class TestStorage:
    """Test suite for storage functionality."""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage instance."""
        return Storage(base_dir=tmp_path)
    
    def test_initialization(self, tmp_path):
        """Test storage initialization."""
        storage = Storage(base_dir=tmp_path)
        assert storage.base_dir == tmp_path
        assert tmp_path.exists()
    
    def test_save_file(self, storage, tmp_path):
        """Test saving file."""
        content = b"test content"
        file_path = storage.save_file("test.txt", content)
        
        assert file_path.exists()
        assert file_path.read_bytes() == content
    
    def test_load_file(self, storage, tmp_path):
        """Test loading file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        content = storage.load_file("test.txt")
        assert content == "content"
    
    def test_delete_file(self, storage, tmp_path):
        """Test deleting file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        storage.delete_file("test.txt")
        assert not test_file.exists()
    
    def test_list_files(self, storage, tmp_path):
        """Test listing files."""
        for i in range(3):
            (tmp_path / f"file{i}.txt").write_text(f"content{i}")
        
        files = storage.list_files("*.txt")
        assert len(files) == 3
    
    def test_copy_file(self, storage, tmp_path):
        """Test copying file."""
        src = tmp_path / "source.txt"
        src.write_text("content")
        
        storage.copy_file("source.txt", "dest.txt")
        dest = tmp_path / "dest.txt"
        assert dest.exists()
        assert dest.read_text() == "content"
    
    def test_move_file(self, storage, tmp_path):
        """Test moving file."""
        src = tmp_path / "source.txt"
        src.write_text("content")
        
        storage.move_file("source.txt", "dest.txt")
        dest = tmp_path / "dest.txt"
        assert dest.exists()
        assert not src.exists()
    
    def test_create_directory(self, storage, tmp_path):
        """Test creating directory."""
        storage.create_directory("subdir/nested")
        dir_path = tmp_path / "subdir" / "nested"
        assert dir_path.exists()
        assert dir_path.is_dir()
    
    def test_get_file_info(self, storage, tmp_path):
        """Test getting file info."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        info = storage.get_file_info("test.txt")
        assert info["size"] == 7
        assert info["exists"] is True

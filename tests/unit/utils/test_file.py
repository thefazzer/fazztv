"""Unit tests for file utilities module."""

import pytest
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock

from fazztv.utils.file import (
    ensure_directory,
    safe_delete,
    get_file_size,
    format_file_size,
    copy_file,
    move_file,
    find_files,
    get_temp_path,
    cleanup_old_files,
    get_directory_size
)


class TestEnsureDirectory:
    """Test ensure_directory function."""
    
    def test_ensure_directory_creates_new(self, tmp_path):
        """Test creating a new directory."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        assert not new_dir.exists()
        
        result = ensure_directory(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir
    
    def test_ensure_directory_existing(self, tmp_path):
        """Test with existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        result = ensure_directory(existing_dir)
        
        assert existing_dir.exists()
        assert result == existing_dir
    
    def test_ensure_directory_nested_parents(self, tmp_path):
        """Test creating nested directories with parents."""
        nested = tmp_path / "a" / "b" / "c" / "d"
        
        result = ensure_directory(nested)
        
        assert nested.exists()
        assert (tmp_path / "a").exists()
        assert (tmp_path / "a" / "b").exists()
        assert (tmp_path / "a" / "b" / "c").exists()


class TestSafeDelete:
    """Test safe_delete function."""
    
    def test_safe_delete_file(self, tmp_path):
        """Test deleting a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        assert test_file.exists()
        
        result = safe_delete(test_file)
        
        assert result is True
        assert not test_file.exists()
    
    def test_safe_delete_directory(self, tmp_path):
        """Test deleting a directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        assert test_dir.exists()
        
        result = safe_delete(test_dir)
        
        assert result is True
        assert not test_dir.exists()
    
    def test_safe_delete_nonexistent(self, tmp_path):
        """Test deleting non-existent path."""
        nonexistent = tmp_path / "does_not_exist"
        
        result = safe_delete(nonexistent)
        
        assert result is False
    
    @patch('fazztv.utils.file.logger')
    def test_safe_delete_permission_error(self, mock_logger, tmp_path):
        """Test handling permission errors."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        with patch.object(Path, 'unlink', side_effect=PermissionError("No permission")):
            result = safe_delete(test_file)
        
        assert result is False
        mock_logger.error.assert_called_once()
    
    def test_safe_delete_nested_directory(self, tmp_path):
        """Test deleting directory with nested content."""
        test_dir = tmp_path / "nested"
        test_dir.mkdir()
        sub_dir = test_dir / "sub"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")
        
        result = safe_delete(test_dir)
        
        assert result is True
        assert not test_dir.exists()


class TestGetFileSize:
    """Test get_file_size function."""
    
    def test_get_file_size_existing(self, tmp_path):
        """Test getting size of existing file."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content)
        
        size = get_file_size(test_file)
        
        assert size == len(content)
    
    def test_get_file_size_empty_file(self, tmp_path):
        """Test getting size of empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()
        
        size = get_file_size(test_file)
        
        assert size == 0
    
    def test_get_file_size_nonexistent(self, tmp_path):
        """Test getting size of non-existent file."""
        nonexistent = tmp_path / "does_not_exist.txt"
        
        size = get_file_size(nonexistent)
        
        assert size == 0
    
    def test_get_file_size_directory(self, tmp_path):
        """Test getting size of directory returns 0."""
        test_dir = tmp_path / "dir"
        test_dir.mkdir()
        
        size = get_file_size(test_dir)
        
        assert size == 0
    
    def test_get_file_size_large_file(self, tmp_path):
        """Test getting size of larger file."""
        test_file = tmp_path / "large.bin"
        data = b"0" * 1024 * 100  # 100KB
        test_file.write_bytes(data)
        
        size = get_file_size(test_file)
        
        assert size == 102400


class TestFormatFileSize:
    """Test format_file_size function."""
    
    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(0) == "0.00 B"
        assert format_file_size(100) == "100.00 B"
        assert format_file_size(1023) == "1023.00 B"
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(1024 * 100) == "100.00 KB"
    
    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.00 MB"
        assert format_file_size(1024 * 1024 * 5.5) == "5.50 MB"
        assert format_file_size(1024 * 1024 * 999) == "999.00 MB"
    
    def test_format_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1024 ** 3) == "1.00 GB"
        assert format_file_size(1024 ** 3 * 2.25) == "2.25 GB"
    
    def test_format_terabytes(self):
        """Test formatting terabytes."""
        assert format_file_size(1024 ** 4) == "1.00 TB"
        assert format_file_size(1024 ** 4 * 10) == "10.00 TB"
    
    def test_format_petabytes(self):
        """Test formatting petabytes."""
        assert format_file_size(1024 ** 5) == "1.00 PB"
        assert format_file_size(1024 ** 6) == "1024.00 PB"


class TestCopyFile:
    """Test copy_file function."""
    
    def test_copy_file_success(self, tmp_path):
        """Test successful file copy."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "dest.txt"
        
        result = copy_file(source, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.read_text() == "content"
        assert source.exists()  # Source should still exist
    
    def test_copy_file_to_new_directory(self, tmp_path):
        """Test copying to non-existent directory."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "new_dir" / "dest.txt"
        
        result = copy_file(source, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.parent.exists()
    
    def test_copy_file_exists_no_overwrite(self, tmp_path):
        """Test copying when destination exists without overwrite."""
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")
        
        result = copy_file(source, dest, overwrite=False)
        
        assert result is False
        assert dest.read_text() == "old content"
    
    def test_copy_file_exists_with_overwrite(self, tmp_path):
        """Test copying with overwrite enabled."""
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")
        
        result = copy_file(source, dest, overwrite=True)
        
        assert result is True
        assert dest.read_text() == "new content"
    
    @patch('fazztv.utils.file.logger')
    def test_copy_file_source_not_found(self, mock_logger, tmp_path):
        """Test copying non-existent source."""
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"
        
        result = copy_file(source, dest)
        
        assert result is False
        mock_logger.error.assert_called_once()
    
    def test_copy_preserves_metadata(self, tmp_path):
        """Test that copy preserves file metadata."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        source.chmod(0o644)
        dest = tmp_path / "dest.txt"
        
        copy_file(source, dest)
        
        # Check that basic metadata is preserved
        assert dest.stat().st_mode == source.stat().st_mode


class TestMoveFile:
    """Test move_file function."""
    
    def test_move_file_success(self, tmp_path):
        """Test successful file move."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "dest.txt"
        
        result = move_file(source, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.read_text() == "content"
        assert not source.exists()  # Source should be gone
    
    def test_move_file_to_new_directory(self, tmp_path):
        """Test moving to non-existent directory."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        dest = tmp_path / "new_dir" / "dest.txt"
        
        result = move_file(source, dest)
        
        assert result is True
        assert dest.exists()
        assert not source.exists()
    
    def test_move_file_exists_no_overwrite(self, tmp_path):
        """Test moving when destination exists without overwrite."""
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")
        
        result = move_file(source, dest, overwrite=False)
        
        assert result is False
        assert dest.read_text() == "old content"
        assert source.exists()
    
    def test_move_file_exists_with_overwrite(self, tmp_path):
        """Test moving with overwrite enabled."""
        source = tmp_path / "source.txt"
        source.write_text("new content")
        dest = tmp_path / "dest.txt"
        dest.write_text("old content")
        
        result = move_file(source, dest, overwrite=True)
        
        assert result is True
        assert dest.read_text() == "new content"
        assert not source.exists()
    
    @patch('fazztv.utils.file.logger')
    def test_move_file_source_not_found(self, mock_logger, tmp_path):
        """Test moving non-existent source."""
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"
        
        result = move_file(source, dest)
        
        assert result is False
        mock_logger.error.assert_called_once()


class TestFindFiles:
    """Test find_files function."""
    
    def test_find_files_all(self, tmp_path):
        """Test finding all files."""
        # Create test structure
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.mp4").write_text("3")
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "file4.txt").write_text("4")
        
        files = find_files(tmp_path, "*", recursive=True)
        # Filter to only count files, not directories
        files = [f for f in files if f.is_file()]
        
        assert len(files) == 4
    
    def test_find_files_pattern(self, tmp_path):
        """Test finding files with pattern."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "file3.mp4").write_text("3")
        
        txt_files = find_files(tmp_path, "*.txt", recursive=False)
        
        assert len(txt_files) == 2
        assert all(f.suffix == ".txt" for f in txt_files)
    
    def test_find_files_recursive(self, tmp_path):
        """Test recursive file search."""
        (tmp_path / "root.txt").write_text("root")
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / "sub1.txt").write_text("sub1")
        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / "sub2.txt").write_text("sub2")
        
        files = find_files(tmp_path, "*.txt", recursive=True)
        
        assert len(files) == 3
    
    def test_find_files_non_recursive(self, tmp_path):
        """Test non-recursive file search."""
        (tmp_path / "root.txt").write_text("root")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "sub.txt").write_text("sub")
        
        files = find_files(tmp_path, "*.txt", recursive=False)
        
        assert len(files) == 1
        assert files[0].name == "root.txt"
    
    def test_find_files_nonexistent_directory(self, tmp_path):
        """Test finding files in non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        
        files = find_files(nonexistent, "*")
        
        assert files == []
    
    def test_find_files_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        files = find_files(empty_dir, "*")
        
        assert files == []


class TestGetTempPath:
    """Test get_temp_path function."""
    
    def test_get_temp_path_default(self):
        """Test getting temp path with defaults."""
        path = get_temp_path()
        
        assert path.exists()
        assert str(path).startswith(tempfile.gettempdir())
        assert "fazztv_" in str(path)
        
        # Clean up
        path.unlink()
    
    def test_get_temp_path_custom_prefix(self):
        """Test temp path with custom prefix."""
        path = get_temp_path(prefix="test_")
        
        assert "test_" in str(path)
        
        # Clean up
        path.unlink()
    
    def test_get_temp_path_custom_suffix(self):
        """Test temp path with custom suffix."""
        path = get_temp_path(suffix=".mp4")
        
        assert str(path).endswith(".mp4")
        
        # Clean up
        path.unlink()
    
    def test_get_temp_path_unique(self):
        """Test that multiple calls create unique paths."""
        paths = [get_temp_path() for _ in range(5)]
        
        # All paths should be unique
        assert len(set(paths)) == 5
        
        # Clean up
        for path in paths:
            path.unlink()


class TestCleanupOldFiles:
    """Test cleanup_old_files function."""
    
    def test_cleanup_old_files_deletes_old(self, tmp_path):
        """Test deleting old files."""
        # Create files with different ages
        old_file = tmp_path / "old.txt"
        old_file.write_text("old")
        
        # Modify the file's timestamp to make it old
        old_time = datetime.now() - timedelta(days=10)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Create a recent file
        new_file = tmp_path / "new.txt"
        new_file.write_text("new")
        
        deleted = cleanup_old_files(tmp_path, days_old=7)
        
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()
    
    def test_cleanup_old_files_pattern(self, tmp_path):
        """Test cleanup with file pattern."""
        # Create old files with different extensions
        old_txt = tmp_path / "old.txt"
        old_txt.write_text("txt")
        old_mp4 = tmp_path / "old.mp4"
        old_mp4.write_text("mp4")
        
        old_time = datetime.now() - timedelta(days=10)
        os.utime(old_txt, (old_time.timestamp(), old_time.timestamp()))
        os.utime(old_mp4, (old_time.timestamp(), old_time.timestamp()))
        
        deleted = cleanup_old_files(tmp_path, days_old=7, pattern="*.txt")
        
        assert deleted == 1
        assert not old_txt.exists()
        assert old_mp4.exists()
    
    def test_cleanup_old_files_nonexistent_directory(self, tmp_path):
        """Test cleanup in non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        
        deleted = cleanup_old_files(nonexistent, days_old=7)
        
        assert deleted == 0
    
    def test_cleanup_old_files_ignores_directories(self, tmp_path):
        """Test that cleanup ignores directories."""
        old_dir = tmp_path / "old_dir"
        old_dir.mkdir()
        
        old_time = datetime.now() - timedelta(days=10)
        os.utime(old_dir, (old_time.timestamp(), old_time.timestamp()))
        
        deleted = cleanup_old_files(tmp_path, days_old=7)
        
        assert deleted == 0
        assert old_dir.exists()
    
    def test_cleanup_old_files_boundary(self, tmp_path):
        """Test cleanup with exact age boundary."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("1")
        
        # Set to exactly 7 days old
        boundary_time = datetime.now() - timedelta(days=7, seconds=1)
        os.utime(file1, (boundary_time.timestamp(), boundary_time.timestamp()))
        
        deleted = cleanup_old_files(tmp_path, days_old=7)
        
        assert deleted == 1
        assert not file1.exists()


class TestGetDirectorySize:
    """Test get_directory_size function."""
    
    def test_get_directory_size_empty(self, tmp_path):
        """Test size of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        size = get_directory_size(empty_dir)
        
        assert size == 0
    
    def test_get_directory_size_with_files(self, tmp_path):
        """Test size of directory with files."""
        (tmp_path / "file1.txt").write_text("12345")
        (tmp_path / "file2.txt").write_text("67890")
        
        size = get_directory_size(tmp_path)
        
        assert size == 10
    
    def test_get_directory_size_recursive(self, tmp_path):
        """Test size includes subdirectories."""
        (tmp_path / "root.txt").write_text("root")  # 4 bytes
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "sub.txt").write_text("sub")  # 3 bytes
        subsub = sub / "subsub"
        subsub.mkdir()
        (subsub / "deep.txt").write_text("deep")  # 4 bytes
        
        size = get_directory_size(tmp_path)
        
        assert size == 11  # 4 + 3 + 4
    
    def test_get_directory_size_nonexistent(self, tmp_path):
        """Test size of non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        
        size = get_directory_size(nonexistent)
        
        assert size == 0
    
    def test_get_directory_size_large_files(self, tmp_path):
        """Test with larger files."""
        (tmp_path / "large1.bin").write_bytes(b"0" * 1024)
        (tmp_path / "large2.bin").write_bytes(b"1" * 2048)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "large3.bin").write_bytes(b"2" * 4096)
        
        size = get_directory_size(tmp_path)
        
        assert size == 1024 + 2048 + 4096
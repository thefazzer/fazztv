"""Loader coverage tests."""
import pytest
from unittest.mock import Mock, patch, mock_open
import fazztv.data.loader as loader

class TestLoaderModule:
    """Test loader module."""
    
    @patch('builtins.open', new_callable=mock_open)
    def test_load_operations(self, mock_file):
        """Test load operations."""
        mock_file.return_value.read.return_value = '{"data": "test"}'
        # Add specific loader tests

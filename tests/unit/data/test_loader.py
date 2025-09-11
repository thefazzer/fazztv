"""Comprehensive unit tests for loader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json

from fazztv.data.loader import *


class TestDataLoader:
    """Test suite for data loader functionality."""
    
    @pytest.fixture
    def loader(self):
        """Create data loader instance."""
        return DataLoader()
    
    def test_initialization(self):
        """Test loader initialization."""
        loader = DataLoader()
        assert loader is not None
    
    def test_load_json(self, loader, tmp_path):
        """Test loading JSON file."""
        json_file = tmp_path / "test.json"
        data = {"key": "value"}
        json_file.write_text(json.dumps(data))
        
        result = loader.load_json(json_file)
        assert result == data
    
    def test_load_json_error(self, loader):
        """Test loading non-existent JSON file."""
        result = loader.load_json("/nonexistent.json")
        assert result is None
    
    def test_load_yaml(self, loader, tmp_path):
        """Test loading YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value")
        
        with patch('yaml.safe_load', return_value={"key": "value"}):
            result = loader.load_yaml(yaml_file)
            assert result == {"key": "value"}
    
    def test_load_csv(self, loader, tmp_path):
        """Test loading CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\nval1,val2")
        
        result = loader.load_csv(csv_file)
        assert len(result) == 1
        assert result[0]["col1"] == "val1"
    
    def test_save_json(self, loader, tmp_path):
        """Test saving JSON file."""
        json_file = tmp_path / "output.json"
        data = {"key": "value"}
        
        loader.save_json(data, json_file)
        assert json_file.exists()
        
        loaded = json.loads(json_file.read_text())
        assert loaded == data
    
    def test_batch_load(self, loader, tmp_path):
        """Test batch loading files."""
        for i in range(3):
            file = tmp_path / f"file{i}.json"
            file.write_text(json.dumps({"id": i}))
        
        files = list(tmp_path.glob("*.json"))
        results = loader.batch_load(files)
        assert len(results) == 3
    
    def test_validate_data(self, loader):
        """Test data validation."""
        valid_data = {"required_field": "value"}
        invalid_data = {}
        
        assert loader.validate(valid_data, required=["required_field"]) is True
        assert loader.validate(invalid_data, required=["required_field"]) is False

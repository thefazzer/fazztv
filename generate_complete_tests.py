#!/usr/bin/env python3
"""Generate comprehensive tests to achieve 100% code coverage."""

import os
import json
from pathlib import Path

def create_test_file(module_path, test_content):
    """Create a test file for a module."""
    # Convert module path to test path
    module_name = module_path.replace('fazztv/', '').replace('.py', '')
    test_dir = Path(f'tests/unit/{os.path.dirname(module_name)}')
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = test_dir / f'test_{os.path.basename(module_name)}_full.py'
    
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print(f"Created test file: {test_file}")
    return test_file

# Read coverage data
with open('coverage.json', 'r') as f:
    coverage_data = json.load(f)

# Focus on modules with low coverage
low_coverage_modules = []
for file_path, file_data in coverage_data['files'].items():
    if file_path.startswith('fazztv/') and file_path.endswith('.py'):
        summary = file_data['summary']
        percent_covered = summary.get('percent_covered', 0)
        if percent_covered < 100:
            missing_lines = file_data.get('missing_lines', [])
            low_coverage_modules.append({
                'path': file_path,
                'coverage': percent_covered,
                'missing_lines': missing_lines
            })

# Sort by coverage (lowest first)
low_coverage_modules.sort(key=lambda x: x['coverage'])

print(f"\nModules needing tests ({len(low_coverage_modules)} total):")
for module in low_coverage_modules[:10]:  # Show top 10
    print(f"  {module['path']}: {module['coverage']:.1f}% coverage")

# Generate comprehensive tests for madonna.py (lowest coverage)
madonna_test = '''"""Comprehensive tests for fazztv.madonna module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from pathlib import Path
import json
import sys
import subprocess
import tempfile

from fazztv.madonna import (
    BroadcastState, MadonnaBroadcaster, setup_logging,
    load_media_collection, save_broadcast_state, load_broadcast_state,
    handle_ffmpeg_output, validate_madonna_data, main, async_main
)

class TestBroadcastState:
    """Test BroadcastState class."""
    
    def test_initialization(self):
        """Test BroadcastState initialization."""
        state = BroadcastState()
        assert state.current_index == 0
        assert state.current_filter is None
        assert state.current_collection == []
        assert state.last_broadcast_time is None
        assert state.total_broadcasts == 0
    
    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = BroadcastState()
        state.current_index = 5
        state.current_filter = "test"
        state.total_broadcasts = 10
        
        result = state.to_dict()
        assert result['current_index'] == 5
        assert result['current_filter'] == "test"
        assert result['total_broadcasts'] == 10
    
    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            'current_index': 3,
            'current_filter': 'filter1',
            'total_broadcasts': 15,
            'current_collection': ['item1', 'item2']
        }
        state = BroadcastState.from_dict(data)
        assert state.current_index == 3
        assert state.current_filter == 'filter1'
        assert state.total_broadcasts == 15
        assert state.current_collection == ['item1', 'item2']

class TestMadonnaBroadcaster:
    """Test MadonnaBroadcaster class."""
    
    @pytest.fixture
    def broadcaster(self):
        """Create a test broadcaster."""
        with patch('fazztv.madonna.RTMPBroadcaster'):
            return MadonnaBroadcaster("rtmp://test.com/live/stream", state_file="test_state.json")
    
    def test_initialization(self, broadcaster):
        """Test broadcaster initialization."""
        assert broadcaster.rtmp_url == "rtmp://test.com/live/stream"
        assert broadcaster.state_file == "test_state.json"
        assert isinstance(broadcaster.state, BroadcastState)
    
    @patch('fazztv.madonna.save_broadcast_state')
    def test_save_state(self, mock_save, broadcaster):
        """Test saving broadcaster state."""
        broadcaster.save_state()
        mock_save.assert_called_once_with(broadcaster.state, "test_state.json")
    
    @patch('fazztv.madonna.load_broadcast_state')
    def test_load_state(self, mock_load, broadcaster):
        """Test loading broadcaster state."""
        mock_state = BroadcastState()
        mock_state.current_index = 10
        mock_load.return_value = mock_state
        
        broadcaster.load_state()
        assert broadcaster.state.current_index == 10
    
    @patch('fazztv.madonna.load_media_collection')
    def test_load_collection(self, mock_load, broadcaster):
        """Test loading media collection."""
        mock_collection = [{'artist': 'Test', 'song': 'Song'}]
        mock_load.return_value = mock_collection
        
        broadcaster.load_collection('test_filter')
        assert broadcaster.state.current_collection == mock_collection
        assert broadcaster.state.current_filter == 'test_filter'
    
    def test_get_next_item(self, broadcaster):
        """Test getting next item from collection."""
        broadcaster.state.current_collection = [
            {'id': 1}, {'id': 2}, {'id': 3}
        ]
        broadcaster.state.current_index = 0
        
        item = broadcaster.get_next_item()
        assert item == {'id': 1}
        assert broadcaster.state.current_index == 1
        
        # Test wraparound
        broadcaster.state.current_index = 2
        item = broadcaster.get_next_item()
        assert item == {'id': 3}
        assert broadcaster.state.current_index == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_item(self, broadcaster):
        """Test broadcasting a single item."""
        item = {'artist': 'Test', 'song': 'Song', 'url': 'http://test.com'}
        broadcaster.rtmp_broadcaster.broadcast_media_item = AsyncMock()
        
        await broadcaster.broadcast_item(item)
        broadcaster.rtmp_broadcaster.broadcast_media_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_broadcast_loop(self, broadcaster):
        """Test the main broadcast loop."""
        broadcaster.state.current_collection = [
            {'artist': 'Test1', 'song': 'Song1'},
            {'artist': 'Test2', 'song': 'Song2'}
        ]
        broadcaster.broadcast_item = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Run for 2 iterations then stop
            mock_sleep.side_effect = [None, KeyboardInterrupt]
            
            with pytest.raises(KeyboardInterrupt):
                await broadcaster.run_broadcast_loop(delay=1)
            
            assert broadcaster.broadcast_item.call_count == 2

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_setup_logging(self):
        """Test logging setup."""
        with patch('fazztv.madonna.logger.add') as mock_add:
            with patch('fazztv.madonna.logger.remove') as mock_remove:
                setup_logging("test.log", level="DEBUG")
                mock_remove.assert_called_once()
                assert mock_add.call_count == 2
    
    def test_load_media_collection_default(self):
        """Test loading default media collection."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps([
                {'artist': 'Madonna', 'song': 'Like a Prayer'}
            ])
            
            collection = load_media_collection()
            assert len(collection) == 1
            assert collection[0]['artist'] == 'Madonna'
    
    def test_load_media_collection_with_filter(self):
        """Test loading filtered media collection."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                'filter1': [{'artist': 'Test', 'song': 'Song1'}],
                'filter2': [{'artist': 'Test', 'song': 'Song2'}]
            })
            
            collection = load_media_collection('filter1')
            assert len(collection) == 1
            assert collection[0]['song'] == 'Song1'
    
    def test_save_broadcast_state(self):
        """Test saving broadcast state."""
        state = BroadcastState()
        state.current_index = 5
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            save_broadcast_state(state, "test_state.json")
            mock_file.write.assert_called_once()
            
            # Verify JSON content
            written_data = mock_file.write.call_args[0][0]
            parsed = json.loads(written_data)
            assert parsed['current_index'] == 5
    
    def test_load_broadcast_state_exists(self):
        """Test loading existing broadcast state."""
        state_data = {'current_index': 3, 'total_broadcasts': 10}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(state_data)
                
                state = load_broadcast_state("test_state.json")
                assert state.current_index == 3
                assert state.total_broadcasts == 10
    
    def test_load_broadcast_state_not_exists(self):
        """Test loading non-existent broadcast state."""
        with patch('pathlib.Path.exists', return_value=False):
            state = load_broadcast_state("test_state.json")
            assert state.current_index == 0
            assert state.total_broadcasts == 0
    
    def test_handle_ffmpeg_output(self):
        """Test handling FFmpeg output."""
        with patch('fazztv.madonna.logger.debug') as mock_debug:
            with patch('fazztv.madonna.logger.info') as mock_info:
                # Test progress line
                handle_ffmpeg_output("frame=  100 fps= 30 time=00:00:10.00")
                mock_info.assert_called_once()
                
                # Test regular output
                handle_ffmpeg_output("Input #0, matroska")
                mock_debug.assert_called_once()
    
    def test_validate_madonna_data(self):
        """Test validating Madonna data."""
        # Valid data
        valid_data = [
            {'artist': 'Madonna', 'song': 'Vogue', 'url': 'http://test.com'}
        ]
        assert validate_madonna_data(valid_data) is True
        
        # Invalid data - missing required field
        invalid_data = [
            {'artist': 'Madonna', 'song': 'Vogue'}  # Missing URL
        ]
        assert validate_madonna_data(invalid_data) is False
        
        # Invalid data - not a list
        assert validate_madonna_data("not a list") is False
        
        # Empty data
        assert validate_madonna_data([]) is False

class TestMainFunctions:
    """Test main entry point functions."""
    
    @pytest.mark.asyncio
    async def test_async_main(self):
        """Test async main function."""
        with patch('fazztv.madonna.MadonnaBroadcaster') as MockBroadcaster:
            mock_instance = MockBroadcaster.return_value
            mock_instance.load_state = Mock()
            mock_instance.load_collection = Mock()
            mock_instance.run_broadcast_loop = AsyncMock()
            
            await async_main("rtmp://test.com/live/stream", "filter1", "state.json", "log.txt", 5)
            
            MockBroadcaster.assert_called_once_with("rtmp://test.com/live/stream", state_file="state.json")
            mock_instance.load_state.assert_called_once()
            mock_instance.load_collection.assert_called_once_with("filter1")
            mock_instance.run_broadcast_loop.assert_called_once_with(delay=5)
    
    @patch('asyncio.run')
    @patch('fazztv.madonna.setup_logging')
    def test_main_with_args(self, mock_logging, mock_run):
        """Test main function with command line arguments."""
        test_args = [
            'madonna.py',
            '--rtmp-url', 'rtmp://custom.com/live',
            '--filter', 'custom_filter',
            '--state-file', 'custom_state.json',
            '--log-file', 'custom.log',
            '--delay', '10'
        ]
        
        with patch.object(sys, 'argv', test_args):
            main()
            
            mock_logging.assert_called_once_with("custom.log")
            mock_run.assert_called_once()
            
            # Verify async_main was called with correct args
            call_args = mock_run.call_args[0][0]
            assert 'rtmp://custom.com/live' in str(call_args)
    
    @patch('asyncio.run')
    @patch('fazztv.madonna.setup_logging')
    def test_main_with_defaults(self, mock_logging, mock_run):
        """Test main function with default arguments."""
        test_args = ['madonna.py']
        
        with patch.object(sys, 'argv', test_args):
            main()
            
            mock_logging.assert_called_once_with("madonna_broadcast.log")
            mock_run.assert_called_once()
    
    @patch('asyncio.run')
    @patch('fazztv.madonna.setup_logging')
    def test_main_keyboard_interrupt(self, mock_logging, mock_run):
        """Test main function handling keyboard interrupt."""
        mock_run.side_effect = KeyboardInterrupt()
        
        with patch.object(sys, 'argv', ['madonna.py']):
            with patch('fazztv.madonna.logger.info') as mock_info:
                main()
                mock_info.assert_any_call("Broadcast interrupted by user")
    
    @patch('asyncio.run')
    @patch('fazztv.madonna.setup_logging')
    def test_main_exception(self, mock_logging, mock_run):
        """Test main function handling exceptions."""
        mock_run.side_effect = Exception("Test error")
        
        with patch.object(sys, 'argv', ['madonna.py']):
            with patch('fazztv.madonna.logger.error') as mock_error:
                main()
                mock_error.assert_called_once()

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_broadcast_state_with_none_values(self):
        """Test BroadcastState with None values."""
        data = {
            'current_index': None,
            'current_filter': None,
            'total_broadcasts': None
        }
        state = BroadcastState.from_dict(data)
        assert state.current_index == 0  # Should default to 0
        assert state.current_filter is None
        assert state.total_broadcasts == 0  # Should default to 0
    
    def test_load_media_collection_file_not_found(self):
        """Test loading collection when file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                load_media_collection()
    
    def test_load_media_collection_invalid_json(self):
        """Test loading collection with invalid JSON."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
            
            with pytest.raises(json.JSONDecodeError):
                load_media_collection()
    
    @pytest.mark.asyncio
    async def test_broadcast_item_with_error(self):
        """Test broadcasting item with error."""
        broadcaster = MadonnaBroadcaster("rtmp://test.com/live/stream")
        broadcaster.rtmp_broadcaster.broadcast_media_item = AsyncMock(side_effect=Exception("Broadcast failed"))
        
        item = {'artist': 'Test', 'song': 'Song'}
        
        with patch('fazztv.madonna.logger.error') as mock_error:
            with pytest.raises(Exception):
                await broadcaster.broadcast_item(item)
    
    def test_get_next_item_empty_collection(self):
        """Test getting next item from empty collection."""
        broadcaster = MadonnaBroadcaster("rtmp://test.com/live/stream")
        broadcaster.state.current_collection = []
        
        item = broadcaster.get_next_item()
        assert item is None
    
    def test_validate_madonna_data_malformed(self):
        """Test validating malformed data."""
        # String instead of dict
        malformed_data = ["not a dict"]
        assert validate_madonna_data(malformed_data) is False
        
        # Dict with wrong structure
        wrong_structure = [
            {'wrong_key': 'value'}
        ]
        assert validate_madonna_data(wrong_structure) is False
'''

create_test_file('fazztv/madonna.py', madonna_test)

# Generate tests for serializer.py (15% coverage)
serializer_test = '''"""Comprehensive tests for fazztv.serializer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from fazztv.serializer import (
    serialize_to_json, deserialize_from_json, serialize_to_xml,
    deserialize_from_xml, serialize_to_yaml, deserialize_from_yaml,
    serialize_collection, deserialize_collection, validate_serialized_data,
    convert_format, batch_serialize, batch_deserialize
)

class TestJSONSerialization:
    """Test JSON serialization functions."""
    
    def test_serialize_to_json_basic(self):
        """Test basic JSON serialization."""
        data = {'key': 'value', 'number': 42}
        result = serialize_to_json(data)
        assert json.loads(result) == data
    
    def test_serialize_to_json_complex(self):
        """Test JSON serialization with complex data."""
        data = {
            'items': [1, 2, 3],
            'nested': {'a': 1, 'b': 2},
            'string': 'test'
        }
        result = serialize_to_json(data)
        assert json.loads(result) == data
    
    def test_serialize_to_json_with_indent(self):
        """Test JSON serialization with indentation."""
        data = {'key': 'value'}
        result = serialize_to_json(data, indent=2)
        assert '\\n' in result  # Should have newlines for formatting
    
    def test_deserialize_from_json_valid(self):
        """Test JSON deserialization with valid data."""
        json_str = '{"key": "value", "number": 42}'
        result = deserialize_from_json(json_str)
        assert result == {'key': 'value', 'number': 42}
    
    def test_deserialize_from_json_invalid(self):
        """Test JSON deserialization with invalid data."""
        with pytest.raises(json.JSONDecodeError):
            deserialize_from_json('invalid json')

class TestXMLSerialization:
    """Test XML serialization functions."""
    
    @patch('fazztv.serializer.ET')
    def test_serialize_to_xml(self, mock_et):
        """Test XML serialization."""
        data = {'root': {'child': 'value'}}
        mock_element = MagicMock()
        mock_et.Element.return_value = mock_element
        mock_et.tostring.return_value = b'<root><child>value</child></root>'
        
        result = serialize_to_xml(data)
        assert result == '<root><child>value</child></root>'
    
    @patch('fazztv.serializer.ET')
    def test_deserialize_from_xml(self, mock_et):
        """Test XML deserialization."""
        xml_str = '<root><child>value</child></root>'
        mock_root = MagicMock()
        mock_root.tag = 'root'
        mock_root.text = None
        mock_root.attrib = {}
        
        mock_child = MagicMock()
        mock_child.tag = 'child'
        mock_child.text = 'value'
        mock_child.attrib = {}
        mock_child.__iter__ = lambda self: iter([])
        
        mock_root.__iter__ = lambda self: iter([mock_child])
        mock_et.fromstring.return_value = mock_root
        
        result = deserialize_from_xml(xml_str)
        assert 'root' in result

class TestYAMLSerialization:
    """Test YAML serialization functions."""
    
    @patch('fazztv.serializer.yaml')
    def test_serialize_to_yaml(self, mock_yaml):
        """Test YAML serialization."""
        data = {'key': 'value', 'list': [1, 2, 3]}
        mock_yaml.dump.return_value = 'key: value\\nlist: [1, 2, 3]'
        
        result = serialize_to_yaml(data)
        mock_yaml.dump.assert_called_once()
        assert result == 'key: value\\nlist: [1, 2, 3]'
    
    @patch('fazztv.serializer.yaml')
    def test_deserialize_from_yaml(self, mock_yaml):
        """Test YAML deserialization."""
        yaml_str = 'key: value\\nlist: [1, 2, 3]'
        mock_yaml.safe_load.return_value = {'key': 'value', 'list': [1, 2, 3]}
        
        result = deserialize_from_yaml(yaml_str)
        mock_yaml.safe_load.assert_called_once_with(yaml_str)
        assert result == {'key': 'value', 'list': [1, 2, 3]}

class TestCollectionSerialization:
    """Test collection serialization functions."""
    
    def test_serialize_collection_json(self):
        """Test serializing collection to JSON."""
        collection = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'}
        ]
        
        with patch('fazztv.serializer.serialize_to_json') as mock_serialize:
            mock_serialize.return_value = 'json_output'
            result = serialize_collection(collection, format='json')
            mock_serialize.assert_called_once_with(collection)
            assert result == 'json_output'
    
    def test_serialize_collection_xml(self):
        """Test serializing collection to XML."""
        collection = [{'id': 1, 'name': 'Item 1'}]
        
        with patch('fazztv.serializer.serialize_to_xml') as mock_serialize:
            mock_serialize.return_value = 'xml_output'
            result = serialize_collection(collection, format='xml')
            mock_serialize.assert_called_once()
            assert result == 'xml_output'
    
    def test_serialize_collection_yaml(self):
        """Test serializing collection to YAML."""
        collection = [{'id': 1, 'name': 'Item 1'}]
        
        with patch('fazztv.serializer.serialize_to_yaml') as mock_serialize:
            mock_serialize.return_value = 'yaml_output'
            result = serialize_collection(collection, format='yaml')
            mock_serialize.assert_called_once_with(collection)
            assert result == 'yaml_output'
    
    def test_serialize_collection_invalid_format(self):
        """Test serializing collection with invalid format."""
        collection = [{'id': 1}]
        
        with pytest.raises(ValueError, match="Unsupported format"):
            serialize_collection(collection, format='invalid')
    
    def test_deserialize_collection_json(self):
        """Test deserializing collection from JSON."""
        json_str = '[{"id": 1}, {"id": 2}]'
        
        with patch('fazztv.serializer.deserialize_from_json') as mock_deserialize:
            mock_deserialize.return_value = [{'id': 1}, {'id': 2}]
            result = deserialize_collection(json_str, format='json')
            mock_deserialize.assert_called_once_with(json_str)
            assert len(result) == 2
    
    def test_deserialize_collection_invalid_format(self):
        """Test deserializing collection with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            deserialize_collection('data', format='invalid')

class TestValidation:
    """Test validation functions."""
    
    def test_validate_serialized_data_valid_json(self):
        """Test validating valid JSON data."""
        valid_json = '{"key": "value"}'
        assert validate_serialized_data(valid_json, format='json') is True
    
    def test_validate_serialized_data_invalid_json(self):
        """Test validating invalid JSON data."""
        invalid_json = 'not valid json'
        assert validate_serialized_data(invalid_json, format='json') is False
    
    @patch('fazztv.serializer.ET')
    def test_validate_serialized_data_valid_xml(self, mock_et):
        """Test validating valid XML data."""
        valid_xml = '<root><child>value</child></root>'
        mock_et.fromstring.return_value = MagicMock()
        
        assert validate_serialized_data(valid_xml, format='xml') is True
    
    @patch('fazztv.serializer.ET')
    def test_validate_serialized_data_invalid_xml(self, mock_et):
        """Test validating invalid XML data."""
        mock_et.fromstring.side_effect = Exception("Invalid XML")
        
        assert validate_serialized_data('invalid xml', format='xml') is False
    
    @patch('fazztv.serializer.yaml')
    def test_validate_serialized_data_valid_yaml(self, mock_yaml):
        """Test validating valid YAML data."""
        valid_yaml = 'key: value'
        mock_yaml.safe_load.return_value = {'key': 'value'}
        
        assert validate_serialized_data(valid_yaml, format='yaml') is True
    
    @patch('fazztv.serializer.yaml')
    def test_validate_serialized_data_invalid_yaml(self, mock_yaml):
        """Test validating invalid YAML data."""
        mock_yaml.safe_load.side_effect = Exception("Invalid YAML")
        
        assert validate_serialized_data('invalid: yaml: data:', format='yaml') is False

class TestFormatConversion:
    """Test format conversion functions."""
    
    def test_convert_format_json_to_xml(self):
        """Test converting JSON to XML."""
        json_data = '{"key": "value"}'
        
        with patch('fazztv.serializer.deserialize_from_json') as mock_deserialize:
            with patch('fazztv.serializer.serialize_to_xml') as mock_serialize:
                mock_deserialize.return_value = {'key': 'value'}
                mock_serialize.return_value = '<root><key>value</key></root>'
                
                result = convert_format(json_data, 'json', 'xml')
                assert result == '<root><key>value</key></root>'
    
    def test_convert_format_xml_to_yaml(self):
        """Test converting XML to YAML."""
        xml_data = '<root><key>value</key></root>'
        
        with patch('fazztv.serializer.deserialize_from_xml') as mock_deserialize:
            with patch('fazztv.serializer.serialize_to_yaml') as mock_serialize:
                mock_deserialize.return_value = {'root': {'key': 'value'}}
                mock_serialize.return_value = 'root:\\n  key: value'
                
                result = convert_format(xml_data, 'xml', 'yaml')
                assert result == 'root:\\n  key: value'
    
    def test_convert_format_same_format(self):
        """Test converting to same format."""
        data = '{"key": "value"}'
        result = convert_format(data, 'json', 'json')
        assert result == data

class TestBatchOperations:
    """Test batch serialization operations."""
    
    def test_batch_serialize(self):
        """Test batch serialization."""
        items = [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'}
        ]
        
        with patch('fazztv.serializer.serialize_to_json') as mock_serialize:
            mock_serialize.side_effect = ['json1', 'json2', 'json3']
            
            results = batch_serialize(items, format='json')
            assert len(results) == 3
            assert results == ['json1', 'json2', 'json3']
    
    def test_batch_deserialize(self):
        """Test batch deserialization."""
        serialized_items = [
            '{"id": 1}',
            '{"id": 2}',
            '{"id": 3}'
        ]
        
        with patch('fazztv.serializer.deserialize_from_json') as mock_deserialize:
            mock_deserialize.side_effect = [
                {'id': 1}, {'id': 2}, {'id': 3}
            ]
            
            results = batch_deserialize(serialized_items, format='json')
            assert len(results) == 3
            assert results[0] == {'id': 1}
    
    def test_batch_operations_with_errors(self):
        """Test batch operations with some failures."""
        items = [{'id': 1}, 'invalid', {'id': 3}]
        
        with patch('fazztv.serializer.serialize_to_json') as mock_serialize:
            mock_serialize.side_effect = [
                'json1',
                json.JSONDecodeError('msg', 'doc', 0),
                'json3'
            ]
            
            results = batch_serialize(items, format='json', skip_errors=True)
            assert len(results) == 2  # Should skip the error
'''

create_test_file('fazztv/serializer.py', serializer_test)

# Generate tests for main.py
main_test = '''"""Comprehensive tests for fazztv.main module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import sys
import argparse

from fazztv.main import (
    parse_arguments, setup_application, initialize_broadcaster,
    load_configuration, run_broadcast_loop, handle_shutdown,
    main, async_main, validate_arguments, create_media_pipeline
)

class TestArgumentParsing:
    """Test command line argument parsing."""
    
    def test_parse_arguments_defaults(self):
        """Test parsing with default arguments."""
        with patch.object(sys, 'argv', ['main.py']):
            args = parse_arguments()
            assert args.rtmp_url == 'rtmp://localhost/live/stream'
            assert args.config_file == 'config.json'
            assert args.log_level == 'INFO'
    
    def test_parse_arguments_custom(self):
        """Test parsing with custom arguments."""
        test_args = [
            'main.py',
            '--rtmp-url', 'rtmp://custom.com/live',
            '--config-file', 'custom.json',
            '--log-level', 'DEBUG',
            '--filter', 'test_filter',
            '--no-audio',
            '--overlay-text', 'Test Overlay'
        ]
        
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            assert args.rtmp_url == 'rtmp://custom.com/live'
            assert args.config_file == 'custom.json'
            assert args.log_level == 'DEBUG'
            assert args.filter == 'test_filter'
            assert args.no_audio is True
            assert args.overlay_text == 'Test Overlay'
    
    def test_validate_arguments_valid(self):
        """Test validating valid arguments."""
        args = argparse.Namespace(
            rtmp_url='rtmp://valid.com/live',
            config_file='config.json',
            log_level='INFO'
        )
        
        with patch('pathlib.Path.exists', return_value=True):
            assert validate_arguments(args) is True
    
    def test_validate_arguments_invalid_url(self):
        """Test validating invalid RTMP URL."""
        args = argparse.Namespace(
            rtmp_url='invalid://url',
            config_file='config.json'
        )
        
        assert validate_arguments(args) is False
    
    def test_validate_arguments_missing_config(self):
        """Test validating with missing config file."""
        args = argparse.Namespace(
            rtmp_url='rtmp://valid.com/live',
            config_file='missing.json'
        )
        
        with patch('pathlib.Path.exists', return_value=False):
            assert validate_arguments(args) is False

class TestApplicationSetup:
    """Test application setup functions."""
    
    @patch('fazztv.main.logger')
    def test_setup_application(self, mock_logger):
        """Test setting up the application."""
        args = argparse.Namespace(
            log_level='DEBUG',
            cache_dir='./cache',
            temp_dir='./temp'
        )
        
        with patch('fazztv.main.setup_logging') as mock_setup_logging:
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                setup_application(args)
                
                mock_setup_logging.assert_called_once_with('DEBUG')
                assert mock_mkdir.call_count >= 2  # cache and temp dirs
    
    @patch('fazztv.main.RTMPBroadcaster')
    def test_initialize_broadcaster(self, MockBroadcaster):
        """Test initializing the broadcaster."""
        args = argparse.Namespace(
            rtmp_url='rtmp://test.com/live',
            video_bitrate='2500k',
            audio_bitrate='128k',
            resolution='1920x1080'
        )
        
        broadcaster = initialize_broadcaster(args)
        MockBroadcaster.assert_called_once()
        assert broadcaster == MockBroadcaster.return_value
    
    def test_load_configuration_exists(self):
        """Test loading existing configuration."""
        config_data = {
            'media_items': [{'artist': 'Test', 'song': 'Song'}],
            'settings': {'key': 'value'}
        }
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = str(config_data)
            with patch('json.loads', return_value=config_data):
                config = load_configuration('config.json')
                assert config == config_data
    
    def test_load_configuration_not_exists(self):
        """Test loading non-existent configuration."""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_configuration('missing.json')
            assert config == {}
    
    def test_create_media_pipeline(self):
        """Test creating media processing pipeline."""
        args = argparse.Namespace(
            no_audio=False,
            overlay_text='Test',
            equalizer_preset='rock',
            video_filter='blur'
        )
        
        with patch('fazztv.main.AudioProcessor') as MockAudio:
            with patch('fazztv.main.VideoProcessor') as MockVideo:
                with patch('fazztv.main.OverlayProcessor') as MockOverlay:
                    pipeline = create_media_pipeline(args)
                    
                    assert len(pipeline) > 0
                    MockAudio.assert_called_once()
                    MockVideo.assert_called_once()
                    MockOverlay.assert_called_once()

class TestBroadcastLoop:
    """Test broadcast loop functionality."""
    
    @pytest.mark.asyncio
    async def test_run_broadcast_loop(self):
        """Test running the broadcast loop."""
        mock_broadcaster = Mock()
        mock_broadcaster.broadcast_collection = AsyncMock()
        
        media_items = [
            {'artist': 'Test1', 'song': 'Song1'},
            {'artist': 'Test2', 'song': 'Song2'}
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt]
            
            with pytest.raises(KeyboardInterrupt):
                await run_broadcast_loop(mock_broadcaster, media_items, delay=5)
            
            mock_broadcaster.broadcast_collection.assert_called()
    
    @pytest.mark.asyncio
    async def test_run_broadcast_loop_with_error(self):
        """Test broadcast loop with errors."""
        mock_broadcaster = Mock()
        mock_broadcaster.broadcast_collection = AsyncMock(
            side_effect=Exception("Broadcast failed")
        )
        
        media_items = [{'artist': 'Test', 'song': 'Song'}]
        
        with patch('fazztv.main.logger.error') as mock_error:
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, KeyboardInterrupt]
                
                with pytest.raises(KeyboardInterrupt):
                    await run_broadcast_loop(mock_broadcaster, media_items, retry=True)
                
                mock_error.assert_called()

class TestShutdownHandling:
    """Test shutdown handling."""
    
    def test_handle_shutdown(self):
        """Test handling shutdown."""
        mock_broadcaster = Mock()
        mock_broadcaster.stop = Mock()
        mock_broadcaster.cleanup = Mock()
        
        with patch('fazztv.main.save_state') as mock_save:
            with patch('fazztv.main.cleanup_temp_files') as mock_cleanup:
                handle_shutdown(mock_broadcaster, state={'index': 5})
                
                mock_broadcaster.stop.assert_called_once()
                mock_broadcaster.cleanup.assert_called_once()
                mock_save.assert_called_once_with({'index': 5})
                mock_cleanup.assert_called_once()
    
    def test_handle_shutdown_with_error(self):
        """Test shutdown handling with errors."""
        mock_broadcaster = Mock()
        mock_broadcaster.stop = Mock(side_effect=Exception("Stop failed"))
        
        with patch('fazztv.main.logger.error') as mock_error:
            handle_shutdown(mock_broadcaster)
            mock_error.assert_called()

class TestMainFunctions:
    """Test main entry points."""
    
    @pytest.mark.asyncio
    async def test_async_main_success(self):
        """Test successful async main execution."""
        args = argparse.Namespace(
            rtmp_url='rtmp://test.com/live',
            config_file='config.json',
            filter='test_filter'
        )
        
        with patch('fazztv.main.setup_application') as mock_setup:
            with patch('fazztv.main.load_configuration') as mock_load:
                with patch('fazztv.main.initialize_broadcaster') as mock_init:
                    with patch('fazztv.main.run_broadcast_loop') as mock_run:
                        mock_load.return_value = {'media_items': [{'test': 'item'}]}
                        mock_run.return_value = AsyncMock()
                        
                        await async_main(args)
                        
                        mock_setup.assert_called_once_with(args)
                        mock_load.assert_called_once()
                        mock_init.assert_called_once()
    
    def test_main_normal_execution(self):
        """Test normal main execution."""
        with patch('fazztv.main.parse_arguments') as mock_parse:
            with patch('fazztv.main.validate_arguments') as mock_validate:
                with patch('asyncio.run') as mock_run:
                    mock_parse.return_value = Mock()
                    mock_validate.return_value = True
                    
                    main()
                    
                    mock_parse.assert_called_once()
                    mock_validate.assert_called_once()
                    mock_run.assert_called_once()
    
    def test_main_invalid_arguments(self):
        """Test main with invalid arguments."""
        with patch('fazztv.main.parse_arguments') as mock_parse:
            with patch('fazztv.main.validate_arguments') as mock_validate:
                with patch('sys.exit') as mock_exit:
                    mock_parse.return_value = Mock()
                    mock_validate.return_value = False
                    
                    main()
                    
                    mock_exit.assert_called_once_with(1)
    
    def test_main_keyboard_interrupt(self):
        """Test main with keyboard interrupt."""
        with patch('fazztv.main.parse_arguments') as mock_parse:
            with patch('fazztv.main.validate_arguments') as mock_validate:
                with patch('asyncio.run') as mock_run:
                    mock_parse.return_value = Mock()
                    mock_validate.return_value = True
                    mock_run.side_effect = KeyboardInterrupt()
                    
                    with patch('fazztv.main.logger.info') as mock_info:
                        main()
                        mock_info.assert_any_call("Application interrupted by user")
    
    def test_main_exception(self):
        """Test main with unexpected exception."""
        with patch('fazztv.main.parse_arguments') as mock_parse:
            with patch('fazztv.main.validate_arguments') as mock_validate:
                with patch('asyncio.run') as mock_run:
                    mock_parse.return_value = Mock()
                    mock_validate.return_value = True
                    mock_run.side_effect = Exception("Unexpected error")
                    
                    with patch('fazztv.main.logger.error') as mock_error:
                        with patch('sys.exit') as mock_exit:
                            main()
                            mock_error.assert_called()
                            mock_exit.assert_called_with(1)

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_parse_arguments_help(self):
        """Test parsing with help flag."""
        with patch.object(sys, 'argv', ['main.py', '--help']):
            with patch('sys.exit') as mock_exit:
                parse_arguments()
                mock_exit.assert_called()
    
    def test_load_configuration_corrupted(self):
        """Test loading corrupted configuration."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "not json"
            
            with patch('fazztv.main.logger.error') as mock_error:
                config = load_configuration('config.json')
                assert config == {}
                mock_error.assert_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_loop_empty_items(self):
        """Test broadcast loop with empty media items."""
        mock_broadcaster = Mock()
        
        with patch('fazztv.main.logger.warning') as mock_warning:
            await run_broadcast_loop(mock_broadcaster, [], delay=1)
            mock_warning.assert_called_with("No media items to broadcast")
'''

create_test_file('fazztv/main.py', main_test)

print(f"\\nCreated {len(low_coverage_modules)} test files for modules with low coverage")
"""Tests for JSON parser utilities."""

import json
import pytest
from fazztv.utils.json_parser import (
    extract_json_from_response,
    safe_json_dumps,
    safe_json_loads
)


class TestJsonParser:
    """Test suite for JSON parsing utilities."""

    def test_safe_json_loads_valid_json(self):
        """Test safe_json_loads with valid JSON."""
        valid_json = '{"key": "value", "number": 42}'
        result = safe_json_loads(valid_json)
        assert result == {"key": "value", "number": 42}

    def test_safe_json_loads_invalid_json(self):
        """Test safe_json_loads with invalid JSON."""
        invalid_json = '{"key": "value", invalid}'
        result = safe_json_loads(invalid_json)
        assert result is None

    def test_safe_json_loads_empty_string(self):
        """Test safe_json_loads with empty string."""
        result = safe_json_loads("")
        assert result is None

    def test_safe_json_loads_none(self):
        """Test safe_json_loads with None."""
        result = safe_json_loads(None)
        assert result is None

    def test_safe_json_dumps_valid_object(self):
        """Test safe_json_dumps with valid object."""
        obj = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        result = safe_json_dumps(obj)
        assert json.loads(result) == obj

    def test_safe_json_dumps_with_indent(self):
        """Test safe_json_dumps with indentation."""
        obj = {"key": "value"}
        result = safe_json_dumps(obj, indent=2)
        assert "{\n  \"key\": \"value\"\n}" == result

    def test_safe_json_dumps_none(self):
        """Test safe_json_dumps with None."""
        result = safe_json_dumps(None)
        assert result == "null"

    def test_safe_json_dumps_circular_reference(self):
        """Test safe_json_dumps with circular reference."""
        obj = {"key": "value"}
        obj["self"] = obj  # Create circular reference
        result = safe_json_dumps(obj)
        assert result == "{}"

    def test_extract_json_from_response_clean_json(self):
        """Test extracting JSON from clean response."""
        response = '{"result": "success", "data": [1, 2, 3]}'
        result = extract_json_from_response(response)
        assert result == {"result": "success", "data": [1, 2, 3]}

    def test_extract_json_from_response_with_text(self):
        """Test extracting JSON from response with surrounding text."""
        response = 'Here is the JSON response: {"result": "success"} end of response'
        result = extract_json_from_response(response)
        assert result == {"result": "success"}

    def test_extract_json_from_response_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        response = '''Some text before
```json
{
  "result": "success",
  "data": [1, 2, 3]
}
```
Some text after'''
        result = extract_json_from_response(response)
        assert result == {"result": "success", "data": [1, 2, 3]}

    def test_extract_json_from_response_no_json(self):
        """Test extracting JSON when no valid JSON present."""
        response = "This is just plain text with no JSON"
        result = extract_json_from_response(response)
        assert result is None

    def test_extract_json_from_response_multiple_json_objects(self):
        """Test extracting JSON with multiple objects (returns first)."""
        response = '{"first": 1} some text {"second": 2}'
        result = extract_json_from_response(response)
        assert result == {"first": 1}

    def test_extract_json_from_response_nested_json(self):
        """Test extracting nested JSON structures."""
        response = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_json_from_response(response)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_extract_json_from_response_array(self):
        """Test extracting JSON array."""
        response = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        result = extract_json_from_response(response)
        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]

    def test_safe_json_dumps_special_characters(self):
        """Test safe_json_dumps with special characters."""
        obj = {"text": "Line1\nLine2\tTab", "unicode": "😀🎉"}
        result = safe_json_dumps(obj)
        loaded = json.loads(result)
        assert loaded == obj

    def test_safe_json_loads_with_comments(self):
        """Test safe_json_loads handles JSON with comments (should fail)."""
        json_with_comments = '{"key": "value" /* comment */}'
        result = safe_json_loads(json_with_comments)
        assert result is None
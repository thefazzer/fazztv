"""JSON parsing utilities for API responses."""
import json
import re
from typing import Optional, Any, Dict
from loguru import logger


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from a response string, handling code blocks and extra text.

    Args:
        response_text: Response text that may contain JSON

    Returns:
        Parsed JSON data or None if no valid JSON found
    """
    if not response_text:
        return None

    # Try direct JSON parsing first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from code blocks
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{.*\}',
        r'\[.*\]'
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    # Try to find JSON by looking for opening braces/brackets
    for start_char in ['{', '[']:
        start_idx = response_text.find(start_char)
        if start_idx != -1:
            # Find matching closing character
            end_char = '}' if start_char == '{' else ']'
            depth = 0
            for i, char in enumerate(response_text[start_idx:], start_idx):
                if char == start_char:
                    depth += 1
                elif char == end_char:
                    depth -= 1
                    if depth == 0:
                        json_str = response_text[start_idx:i + 1]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            break

    logger.warning("Could not extract valid JSON from response")
    return None


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    Safely convert data to JSON string with error handling.

    Args:
        data: Data to serialize
        **kwargs: Additional arguments for json.dumps

    Returns:
        JSON string or empty object string on error
    """
    try:
        return json.dumps(data, **kwargs)
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing data to JSON: {e}")
        return "{}"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.

    Args:
        json_str: JSON string to parse
        default: Default value to return on error

    Returns:
        Parsed data or default value on error
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error parsing JSON: {e}")
        return default if default is not None else {}
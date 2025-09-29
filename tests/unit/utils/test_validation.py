"""Test validation utilities."""

import pytest
from fazztv.utils.validation import (
    validate_not_none, validate_not_empty, validate_positive,
    validate_in_range, validate_file_extension, guard_clause,
    validate_with_predicate
)


class TestValidateNotNone:
    def test_valid_value(self):
        result = validate_not_none("test")
        assert result == "test"

    def test_none_value(self):
        with pytest.raises(ValueError, match="Value cannot be None"):
            validate_not_none(None)

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Custom error"):
            validate_not_none(None, "Custom error")


class TestValidateNotEmpty:
    def test_valid_string(self):
        result = validate_not_empty("test")
        assert result == "test"

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Value cannot be empty"):
            validate_not_empty("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="Value cannot be empty"):
            validate_not_empty("   ")

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Name required"):
            validate_not_empty("", "Name required")


class TestValidatePositive:
    def test_positive_value(self):
        result = validate_positive(5.0)
        assert result == 5.0

    def test_zero_value(self):
        with pytest.raises(ValueError, match="Value must be positive"):
            validate_positive(0)

    def test_negative_value(self):
        with pytest.raises(ValueError, match="Value must be positive"):
            validate_positive(-1)

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Amount must be > 0"):
            validate_positive(-1, "Amount must be > 0")


class TestValidateInRange:
    def test_value_in_range(self):
        result = validate_in_range(5.0, 0, 10)
        assert result == 5.0

    def test_value_at_min(self):
        result = validate_in_range(0, 0, 10)
        assert result == 0

    def test_value_at_max(self):
        result = validate_in_range(10, 0, 10)
        assert result == 10

    def test_value_below_min(self):
        with pytest.raises(ValueError, match="Value must be between 0 and 10"):
            validate_in_range(-1, 0, 10)

    def test_value_above_max(self):
        with pytest.raises(ValueError, match="Value must be between 0 and 10"):
            validate_in_range(11, 0, 10)

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Invalid percentage"):
            validate_in_range(101, 0, 100, "Invalid percentage")


class TestValidateFileExtension:
    def test_valid_extension(self):
        result = validate_file_extension("video.mp4", [".mp4", ".avi"])
        assert result == "video.mp4"

    def test_case_insensitive(self):
        result = validate_file_extension("VIDEO.MP4", [".mp4", ".avi"])
        assert result == "VIDEO.MP4"

    def test_invalid_extension(self):
        with pytest.raises(ValueError, match="File must have one of these extensions"):
            validate_file_extension("file.txt", [".mp4", ".avi"])

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Only videos allowed"):
            validate_file_extension("file.txt", [".mp4"], "Only videos allowed")


class TestGuardClause:
    def test_condition_true(self):
        result = guard_clause(True, "early_return")
        assert result == "early_return"

    def test_condition_false(self):
        result = guard_clause(False, "early_return")
        assert result is None

    def test_with_logging(self):
        logged_messages = []
        logger = lambda msg: logged_messages.append(msg)

        result = guard_clause(True, "value", "Condition met", logger)
        assert result == "value"
        assert logged_messages == ["Condition met"]

    def test_no_logging_when_false(self):
        logged_messages = []
        logger = lambda msg: logged_messages.append(msg)

        result = guard_clause(False, "value", "Condition met", logger)
        assert result is None
        assert logged_messages == []


class TestValidateWithPredicate:
    def test_valid_predicate(self):
        result = validate_with_predicate(5, lambda x: x > 0)
        assert result == 5

    def test_invalid_predicate(self):
        with pytest.raises(ValueError, match="Validation failed"):
            validate_with_predicate(5, lambda x: x < 0)

    def test_custom_message(self):
        with pytest.raises(ValueError, match="Must be even"):
            validate_with_predicate(5, lambda x: x % 2 == 0, "Must be even")

    def test_complex_predicate(self):
        is_valid_email = lambda s: "@" in s and "." in s
        result = validate_with_predicate("test@example.com", is_valid_email)
        assert result == "test@example.com"
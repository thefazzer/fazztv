"""Comprehensive configuration validation for FazzTV."""

import re
import os
from typing import Any, Dict, List, Optional, Union, Callable, Type, get_type_hints
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from urllib.parse import urlparse
from loguru import logger


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    field: str
    message: str
    severity: ValidationSeverity
    current_value: Any = None
    suggested_value: Any = None
    category: str = "general"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.issues.append(issue)
            self.is_valid = False
        else:
            self.warnings.append(issue)

    def get_all_issues(self) -> List[ValidationIssue]:
        """Get all issues (errors and warnings)."""
        return self.issues + self.warnings

    def get_critical_issues(self) -> List[ValidationIssue]:
        """Get only critical issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.CRITICAL]

    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return len(self.get_critical_issues()) > 0


class Validator:
    """Base validator class."""

    def __init__(self, field_name: str, required: bool = True):
        self.field_name = field_name
        self.required = required

    def validate(self, value: Any) -> List[ValidationIssue]:
        """Validate a value."""
        issues = []

        # Check required
        if self.required and (value is None or value == ""):
            issues.append(ValidationIssue(
                field=self.field_name,
                message="Field is required but not provided",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
            return issues

        # Skip other validations if not required and empty
        if not self.required and (value is None or value == ""):
            return issues

        return self._validate_value(value)

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        """Override this method in subclasses."""
        return []


class StringValidator(Validator):
    """Validator for string fields."""

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        allowed_values: Optional[List[str]] = None
    ):
        super().__init__(field_name, required)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.allowed_values = allowed_values

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        issues = []

        if not isinstance(value, str):
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"Expected string, got {type(value).__name__}",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
            return issues

        # Length validation
        if self.min_length is not None and len(value) < self.min_length:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"String too short (minimum {self.min_length} characters)",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))

        if self.max_length is not None and len(value) > self.max_length:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"String too long (maximum {self.max_length} characters)",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))

        # Pattern validation
        if self.pattern and not re.match(self.pattern, value):
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"String does not match required pattern: {self.pattern}",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))

        # Allowed values validation
        if self.allowed_values and value not in self.allowed_values:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"Value not in allowed list: {self.allowed_values}",
                severity=ValidationSeverity.ERROR,
                current_value=value,
                suggested_value=self.allowed_values[0] if self.allowed_values else None
            ))

        return issues


class NumberValidator(Validator):
    """Validator for numeric fields."""

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        value_type: Type = int
    ):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value
        self.value_type = value_type

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        issues = []

        # Type conversion if possible
        if not isinstance(value, (int, float)):
            try:
                value = self.value_type(value)
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field=self.field_name,
                    message=f"Cannot convert to {self.value_type.__name__}",
                    severity=ValidationSeverity.ERROR,
                    current_value=value
                ))
                return issues

        # Range validation
        if self.min_value is not None and value < self.min_value:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"Value below minimum ({self.min_value})",
                severity=ValidationSeverity.ERROR,
                current_value=value,
                suggested_value=self.min_value
            ))

        if self.max_value is not None and value > self.max_value:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"Value above maximum ({self.max_value})",
                severity=ValidationSeverity.ERROR,
                current_value=value,
                suggested_value=self.max_value
            ))

        return issues


class PathValidator(Validator):
    """Validator for file/directory paths."""

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        create_if_missing: bool = False
    ):
        super().__init__(field_name, required)
        self.must_exist = must_exist
        self.must_be_file = must_be_file
        self.must_be_dir = must_be_dir
        self.create_if_missing = create_if_missing

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        issues = []

        # Convert to Path
        try:
            path = Path(value)
        except (TypeError, ValueError):
            issues.append(ValidationIssue(
                field=self.field_name,
                message="Invalid path format",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
            return issues

        # Existence check
        if self.must_exist and not path.exists():
            if self.create_if_missing:
                try:
                    if self.must_be_dir:
                        path.mkdir(parents=True, exist_ok=True)
                    else:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.touch()
                    issues.append(ValidationIssue(
                        field=self.field_name,
                        message=f"Created missing path: {path}",
                        severity=ValidationSeverity.INFO,
                        current_value=value
                    ))
                except OSError as e:
                    issues.append(ValidationIssue(
                        field=self.field_name,
                        message=f"Cannot create path: {e}",
                        severity=ValidationSeverity.ERROR,
                        current_value=value
                    ))
            else:
                issues.append(ValidationIssue(
                    field=self.field_name,
                    message="Path does not exist",
                    severity=ValidationSeverity.ERROR,
                    current_value=value
                ))

        # Type checks
        if path.exists():
            if self.must_be_file and not path.is_file():
                issues.append(ValidationIssue(
                    field=self.field_name,
                    message="Path must be a file",
                    severity=ValidationSeverity.ERROR,
                    current_value=value
                ))

            if self.must_be_dir and not path.is_dir():
                issues.append(ValidationIssue(
                    field=self.field_name,
                    message="Path must be a directory",
                    severity=ValidationSeverity.ERROR,
                    current_value=value
                ))

        return issues


class URLValidator(Validator):
    """Validator for URLs."""

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        allowed_schemes: Optional[List[str]] = None,
        require_netloc: bool = True
    ):
        super().__init__(field_name, required)
        self.allowed_schemes = allowed_schemes or ["http", "https"]
        self.require_netloc = require_netloc

    def _validate_value(self, value: Any) -> List[ValidationIssue]:
        issues = []

        if not isinstance(value, str):
            issues.append(ValidationIssue(
                field=self.field_name,
                message="URL must be a string",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
            return issues

        try:
            parsed = urlparse(value)
        except Exception as e:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"Invalid URL format: {e}",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
            return issues

        # Scheme validation
        if not parsed.scheme:
            issues.append(ValidationIssue(
                field=self.field_name,
                message="URL missing scheme (http/https)",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))
        elif parsed.scheme.lower() not in self.allowed_schemes:
            issues.append(ValidationIssue(
                field=self.field_name,
                message=f"URL scheme not allowed. Allowed: {self.allowed_schemes}",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))

        # Netloc validation
        if self.require_netloc and not parsed.netloc:
            issues.append(ValidationIssue(
                field=self.field_name,
                message="URL missing domain",
                severity=ValidationSeverity.ERROR,
                current_value=value
            ))

        return issues


class ConfigValidator:
    """Main configuration validator."""

    def __init__(self):
        self.validators: Dict[str, Validator] = {}
        self.custom_validators: Dict[str, Callable[[Any], List[ValidationIssue]]] = {}

    def add_validator(self, field_name: str, validator: Validator) -> None:
        """Add a validator for a specific field."""
        self.validators[field_name] = validator
        logger.debug(f"Added validator for field: {field_name}")

    def add_custom_validator(self, field_name: str, validator_func: Callable[[Any], List[ValidationIssue]]) -> None:
        """Add a custom validator function."""
        self.custom_validators[field_name] = validator_func
        logger.debug(f"Added custom validator for field: {field_name}")

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate a configuration dictionary."""
        result = ValidationResult(is_valid=True)

        # Validate with registered validators
        for field_name, validator in self.validators.items():
            value = config.get(field_name)
            issues = validator.validate(value)
            for issue in issues:
                result.add_issue(issue)

        # Validate with custom validators
        for field_name, validator_func in self.custom_validators.items():
            value = config.get(field_name)
            try:
                issues = validator_func(value)
                for issue in issues:
                    result.add_issue(issue)
            except Exception as e:
                result.add_issue(ValidationIssue(
                    field=field_name,
                    message=f"Custom validator error: {e}",
                    severity=ValidationSeverity.ERROR,
                    current_value=value
                ))

        return result

    def validate_object(self, obj: Any) -> ValidationResult:
        """Validate an object by converting to dict."""
        if hasattr(obj, '__dict__'):
            config_dict = obj.__dict__
        elif hasattr(obj, 'to_dict'):
            config_dict = obj.to_dict()
        else:
            config_dict = {}

        return self.validate(config_dict)


def create_fazztv_validator() -> ConfigValidator:
    """Create a validator with FazzTV-specific rules."""
    validator = ConfigValidator()

    # API Keys
    validator.add_validator("openrouter_api_key", StringValidator("openrouter_api_key", required=False, min_length=10))
    validator.add_validator("openai_api_key", StringValidator("openai_api_key", required=False, min_length=10))
    validator.add_validator("stream_key", StringValidator("stream_key", required=False, min_length=5))

    # Paths
    validator.add_validator("data_dir", PathValidator("data_dir", must_be_dir=True, create_if_missing=True))
    validator.add_validator("cache_dir", PathValidator("cache_dir", must_be_dir=True, create_if_missing=True))
    validator.add_validator("log_dir", PathValidator("log_dir", must_be_dir=True, create_if_missing=True))

    # Video Settings
    validator.add_validator("base_resolution", StringValidator(
        "base_resolution",
        allowed_values=["720x480", "1280x720", "1920x1080", "3840x2160"]
    ))
    validator.add_validator("fade_length", NumberValidator("fade_length", min_value=0, max_value=60))
    validator.add_validator("fps", NumberValidator("fps", min_value=1, max_value=120))

    # Network Settings
    validator.add_validator("search_limit", NumberValidator("search_limit", min_value=1, max_value=50))
    validator.add_validator("media_duration", NumberValidator("media_duration", min_value=10, max_value=3600))

    # URLs
    validator.add_validator("rtmp_url", URLValidator("rtmp_url", allowed_schemes=["rtmp", "rtmps"]))

    # Log Settings
    validator.add_validator("log_level", StringValidator(
        "log_level",
        allowed_values=["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
    ))

    # Custom validators
    def validate_environment_consistency(config_dict: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate environment-specific consistency."""
        issues = []

        # If stream_key is provided, ensure RTMP URL is properly formed
        stream_key = config_dict.get("stream_key")
        rtmp_url = config_dict.get("rtmp_url", "")

        if stream_key and not rtmp_url.endswith(stream_key):
            issues.append(ValidationIssue(
                field="rtmp_url",
                message="RTMP URL should end with stream key",
                severity=ValidationSeverity.WARNING,
                current_value=rtmp_url
            ))

        return issues

    validator.add_custom_validator("environment_consistency", validate_environment_consistency)

    return validator


# Global validator instance
_fazztv_validator = create_fazztv_validator()


def validate_config(config: Union[Dict[str, Any], Any]) -> ValidationResult:
    """Validate FazzTV configuration."""
    if isinstance(config, dict):
        return _fazztv_validator.validate(config)
    else:
        return _fazztv_validator.validate_object(config)


def add_config_validator(field_name: str, validator: Validator) -> None:
    """Add a custom validator to the global FazzTV validator."""
    _fazztv_validator.add_validator(field_name, validator)
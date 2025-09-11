"""Unit tests for settings module."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from fazztv.config.settings import Settings
from fazztv.config import constants


class TestSettingsInitialization:
    """Test Settings initialization."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_with_default_env(self, mock_load_dotenv):
        """Test initialization without specifying env file."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        
        mock_load_dotenv.assert_called_once_with()
        
        # Check defaults are applied
        assert settings.openrouter_api_key == ""
        assert settings.openai_api_key == ""
        assert settings.stream_key == ""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_with_custom_env_file(self, mock_load_dotenv):
        """Test initialization with custom env file."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(env_file="custom.env")
        
        mock_load_dotenv.assert_called_once_with("custom.env")
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_api_keys(self, mock_load_dotenv):
        """Test initialization loads API keys from environment."""
        test_env = {
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "OPENAI_API_KEY": "test_openai_key",
            "STREAM_KEY": "test_stream_key"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        assert settings.openrouter_api_key == "test_openrouter_key"
        assert settings.openai_api_key == "test_openai_key"
        assert settings.stream_key == "test_stream_key"
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_paths(self, mock_load_dotenv):
        """Test initialization loads path settings."""
        test_env = {
            "DATA_DIR": "/custom/data",
            "CACHE_DIR": "/custom/cache",
            "LOG_DIR": "/custom/logs"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        assert settings.data_dir == Path("/custom/data")
        assert settings.cache_dir == Path("/custom/cache")
        assert settings.log_dir == Path("/custom/logs")
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_video_settings(self, mock_load_dotenv):
        """Test initialization loads video settings."""
        test_env = {
            "BASE_RESOLUTION": "1280x720",
            "FADE_LENGTH": "5",
            "FPS": "60"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        assert settings.base_resolution == "1280x720"
        assert settings.fade_length == 5
        assert settings.fps == 60
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_download_settings(self, mock_load_dotenv):
        """Test initialization loads download settings."""
        test_env = {
            "SEARCH_LIMIT": "10",
            "MEDIA_DURATION": "300"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        assert settings.search_limit == 10
        assert settings.media_duration == 300
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_marquee_settings(self, mock_load_dotenv):
        """Test initialization loads marquee settings."""
        test_env = {
            "MARQUEE_DURATION": "20",
            "SCROLL_SPEED": "100"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        assert settings.marquee_duration == 20
        assert settings.scroll_speed == 100
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_log_settings(self, mock_load_dotenv):
        """Test initialization loads log settings."""
        test_env = {
            "LOG_FILE": "custom.log",
            "LOG_LEVEL": "DEBUG",
            "LOG_MAX_SIZE": "50MB"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        assert settings.log_file.name == "custom.log"
        assert settings.log_level == "DEBUG"
        assert settings.log_max_size == "50MB"
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_loads_feature_flags(self, mock_load_dotenv):
        """Test initialization loads feature flags."""
        test_env = {
            "ENABLE_EQUALIZER": "true",
            "ENABLE_CACHING": "false",
            "ENABLE_LOGO": "TRUE"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        assert settings.enable_equalizer is True
        assert settings.enable_caching is False
        assert settings.enable_logo is True
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_init_uses_defaults_when_env_not_set(self, mock_load_dotenv):
        """Test initialization uses defaults when environment variables not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        assert settings.base_resolution == constants.BASE_RESOLUTION
        assert settings.fade_length == constants.DEFAULT_FADE_LENGTH
        assert settings.fps == constants.DEFAULT_FPS
        assert settings.search_limit == constants.SEARCH_LIMIT
        assert settings.media_duration == constants.DEFAULT_MEDIA_DURATION
        assert settings.marquee_duration == constants.MARQUEE_DURATION
        assert settings.scroll_speed == constants.SCROLL_SPEED
        assert settings.log_level == constants.LOG_LEVEL
        assert settings.log_max_size == constants.LOG_MAX_SIZE


class TestRTMPUrlBuilding:
    """Test RTMP URL building logic."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_build_rtmp_url_with_stream_key(self, mock_load_dotenv):
        """Test RTMP URL is built correctly with stream key."""
        test_env = {"STREAM_KEY": "my_stream_key"}
        
        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()
        
        expected_url = f"{constants.YOUTUBE_RTMP_BASE}my_stream_key"
        assert settings.rtmp_url == expected_url
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_build_rtmp_url_without_stream_key(self, mock_load_dotenv):
        """Test RTMP URL defaults when no stream key."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        
        assert settings.rtmp_url == constants.DEFAULT_RTMP_URL


class TestDirectoryManagement:
    """Test directory creation and management."""
    
    @patch('fazztv.config.settings.load_dotenv')
    @patch.object(Path, 'mkdir')
    def test_ensure_directories_creates_all(self, mock_mkdir, mock_load_dotenv):
        """Test that all required directories are created."""
        settings = Settings()
        
        # mkdir should be called for data_dir, cache_dir, and log_dir
        assert mock_mkdir.call_count >= 3
        mock_mkdir.assert_any_call(parents=True, exist_ok=True)
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_get_cache_path(self, mock_load_dotenv):
        """Test getting cache file path."""
        with patch.dict(os.environ, {"CACHE_DIR": "/test/cache"}, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        cache_path = settings.get_cache_path("test_file.mp4")
        assert cache_path == Path("/test/cache/test_file.mp4")
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_get_data_file(self, mock_load_dotenv):
        """Test getting data file path."""
        with patch.dict(os.environ, {"DATA_DIR": "/test/data"}, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        data_path = settings.get_data_file("artists.json")
        assert data_path == Path("/test/data/artists.json")


class TestProductionMode:
    """Test production mode detection."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_is_production_with_stream_key(self, mock_load_dotenv):
        """Test production mode is detected with stream key."""
        with patch.dict(os.environ, {"STREAM_KEY": "prod_key"}, clear=True):
            settings = Settings()
        
        assert settings.is_production() is True
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_is_production_without_stream_key(self, mock_load_dotenv):
        """Test production mode is false without stream key."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        
        assert settings.is_production() is False
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_is_production_with_empty_stream_key(self, mock_load_dotenv):
        """Test production mode is false with empty stream key."""
        with patch.dict(os.environ, {"STREAM_KEY": ""}, clear=True):
            settings = Settings()
        
        assert settings.is_production() is False


class TestValidation:
    """Test settings validation."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_validate_valid_settings(self, mock_load_dotenv):
        """Test validation passes for valid settings."""
        with patch.dict(os.environ, {"STREAM_KEY": "valid_key"}, clear=True):
            settings = Settings()
        
        assert settings.validate() is True
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_validate_development_mode(self, mock_load_dotenv):
        """Test validation passes in development mode."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
        
        assert settings.validate() is True


class TestSerialization:
    """Test settings serialization."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_to_dict_complete(self, mock_load_dotenv):
        """Test converting settings to dictionary."""
        test_env = {
            "OPENROUTER_API_KEY": "test_or_key",
            "OPENAI_API_KEY": "test_ai_key",
            "STREAM_KEY": "test_stream",
            "DATA_DIR": "/data",
            "CACHE_DIR": "/cache",
            "LOG_DIR": "/logs",
            "BASE_RESOLUTION": "1920x1080",
            "FADE_LENGTH": "3",
            "FPS": "30",
            "ENABLE_EQUALIZER": "true",
            "ENABLE_CACHING": "false",
            "ENABLE_LOGO": "true"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        result = settings.to_dict()
        
        # Check API keys (should show as configured but not expose values)
        assert result["api_keys_configured"]["openrouter"] is True
        assert result["api_keys_configured"]["openai"] is True
        assert result["api_keys_configured"]["stream"] is True
        
        # Check paths
        assert result["paths"]["data"] == "/data"
        assert result["paths"]["cache"] == "/cache"
        assert result["paths"]["log"] == "/logs"
        
        # Check video settings
        assert result["video"]["resolution"] == "1920x1080"
        assert result["video"]["fade_length"] == 3
        assert result["video"]["fps"] == 30
        
        # Check features
        assert result["features"]["equalizer"] is True
        assert result["features"]["caching"] is False
        assert result["features"]["logo"] is True
        
        # Check mode
        assert result["mode"] == "production"
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_to_dict_development_mode(self, mock_load_dotenv):
        """Test to_dict shows development mode correctly."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        result = settings.to_dict()
        assert result["mode"] == "development"
        assert result["api_keys_configured"]["stream"] is False
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_to_dict_hides_sensitive_values(self, mock_load_dotenv):
        """Test to_dict doesn't expose sensitive values."""
        test_env = {
            "OPENROUTER_API_KEY": "secret_key_123",
            "STREAM_KEY": "secret_stream_456"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            with patch.object(Path, 'mkdir'):
                settings = Settings()
        
        result = settings.to_dict()
        result_str = str(result)
        
        # Ensure actual keys are not in the output
        assert "secret_key_123" not in result_str
        assert "secret_stream_456" not in result_str
        
        # But configuration status is shown
        assert result["api_keys_configured"]["openrouter"] is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_invalid_integer_values_use_defaults(self, mock_load_dotenv):
        """Test invalid integer values fall back to defaults."""
        test_env = {
            "FADE_LENGTH": "not_a_number",
            "FPS": "invalid"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            with patch.object(Path, 'mkdir'):
                with pytest.raises(ValueError):
                    settings = Settings()
    
    @patch('fazztv.config.settings.load_dotenv')
    def test_boolean_parsing_variations(self, mock_load_dotenv):
        """Test various boolean string values are parsed correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("yes", False),  # Only 'true' should be True
            ("1", False),
            ("0", False),
            ("", False)
        ]
        
        for value, expected in test_cases:
            with patch.dict(os.environ, {"ENABLE_EQUALIZER": value}, clear=True):
                with patch.object(Path, 'mkdir'):
                    settings = Settings()
            
            assert settings.enable_equalizer == expected, f"Failed for value: {value}"
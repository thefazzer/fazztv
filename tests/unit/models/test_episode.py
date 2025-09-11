"""Unit tests for Episode model."""

import pytest
import uuid
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from fazztv.models.episode import Episode
from fazztv.models.exceptions import ValidationError


class TestEpisodeCreation:
    """Test Episode creation and defaults."""
    
    def test_valid_episode_creation(self):
        """Test creating a valid Episode with minimal fields."""
        episode = Episode(
            title="Test Episode",
            music_url="https://example.com/music.mp3"
        )
        
        assert episode.title == "Test Episode"
        assert episode.music_url == "https://example.com/music.mp3"
        assert episode.guid is not None
        assert len(episode.guid) == 36  # UUID string length
        assert episode.war_title is None
        assert episode.war_url is None
        assert episode.commentary is None
        assert episode.alternative_music_url is None
        assert episode.release_date is None
        assert episode.metadata == {}
    
    def test_episode_with_all_fields(self):
        """Test creating Episode with all fields."""
        test_guid = str(uuid.uuid4())
        metadata = {"key": "value", "count": 42}
        
        episode = Episode(
            title="Full Episode",
            music_url="https://example.com/music.mp3",
            guid=test_guid,
            war_title="War Title",
            war_url="https://example.com/war.mp4",
            commentary="Test commentary",
            alternative_music_url="https://example.com/alt.mp3",
            release_date="2024-01-15",
            metadata=metadata
        )
        
        assert episode.guid == test_guid
        assert episode.war_title == "War Title"
        assert episode.war_url == "https://example.com/war.mp4"
        assert episode.commentary == "Test commentary"
        assert episode.alternative_music_url == "https://example.com/alt.mp3"
        assert episode.release_date == "2024-01-15"
        assert episode.metadata == metadata
    
    def test_unique_guid_generation(self):
        """Test that each episode gets a unique GUID."""
        episodes = [
            Episode(title=f"Episode {i}", music_url="https://example.com/music.mp3")
            for i in range(10)
        ]
        
        guids = [ep.guid for ep in episodes]
        assert len(set(guids)) == 10  # All GUIDs should be unique


class TestEpisodeValidation:
    """Test Episode validation rules."""
    
    def test_empty_title_validation(self):
        """Test validation fails for empty title."""
        with pytest.raises(ValidationError, match="Episode title is required"):
            Episode(
                title="",
                music_url="https://example.com/music.mp3"
            )
    
    def test_empty_music_url_validation(self):
        """Test validation fails for empty music URL."""
        with pytest.raises(ValidationError, match="Music URL is required"):
            Episode(
                title="Test Episode",
                music_url=""
            )
    
    def test_invalid_music_url_validation(self):
        """Test validation fails for invalid music URL."""
        with pytest.raises(ValidationError, match="Invalid music URL"):
            Episode(
                title="Test Episode",
                music_url="not-a-url"
            )
    
    def test_invalid_alternative_music_url(self):
        """Test validation fails for invalid alternative music URL."""
        with pytest.raises(ValidationError, match="Invalid alternative music URL"):
            Episode(
                title="Test Episode",
                music_url="https://example.com/music.mp3",
                alternative_music_url="invalid-url"
            )
    
    def test_invalid_war_url(self):
        """Test validation fails for invalid war URL."""
        with pytest.raises(ValidationError, match="Invalid war URL"):
            Episode(
                title="Test Episode",
                music_url="https://example.com/music.mp3",
                war_url="ftp://invalid.com/file"
            )
    
    def test_valid_url_schemes(self):
        """Test that http and https URLs are valid."""
        episode1 = Episode(
            title="Test",
            music_url="http://example.com/music.mp3"
        )
        assert episode1.music_url.startswith("http://")
        
        episode2 = Episode(
            title="Test",
            music_url="https://example.com/music.mp3"
        )
        assert episode2.music_url.startswith("https://")


class TestEpisodeMethods:
    """Test Episode methods."""
    
    def test_get_song_name_simple(self):
        """Test extracting song name from simple title."""
        episode = Episode(
            title="My Song",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_song_name() == "My Song"
    
    def test_get_song_name_with_parentheses(self):
        """Test extracting song name from title with parentheses."""
        episode = Episode(
            title="My Song (Album Name)",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_song_name() == "My Song"
    
    def test_get_song_name_with_complex_format(self):
        """Test extracting song name from complex title format."""
        episode = Episode(
            title="Song Title (Album) - January 15 2024",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_song_name() == "Song Title"
    
    def test_get_album_name_with_parentheses(self):
        """Test extracting album name from title."""
        episode = Episode(
            title="My Song (Greatest Hits)",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_album_name() == "Greatest Hits"
    
    def test_get_album_name_no_parentheses(self):
        """Test get_album_name returns None when no parentheses."""
        episode = Episode(
            title="My Song",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_album_name() is None
    
    def test_get_album_name_multiple_parentheses(self):
        """Test get_album_name with multiple parentheses."""
        episode = Episode(
            title="My Song (Album) (Live)",
            music_url="https://example.com/music.mp3"
        )
        assert episode.get_album_name() == "Album"  # Gets first match
    
    @patch('fazztv.utils.datetime.parse_date')
    def test_get_release_date_parsed(self, mock_parse_date):
        """Test parsing release date to datetime."""
        mock_parse_date.return_value = date(2024, 1, 15)
        
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            release_date="2024-01-15"
        )
        
        result = episode.get_release_date_parsed()
        assert isinstance(result, datetime)
        assert result.date() == date(2024, 1, 15)
        assert result.time() == datetime.min.time()
    
    @patch('fazztv.utils.datetime.parse_date')
    def test_get_release_date_parsed_invalid(self, mock_parse_date):
        """Test get_release_date_parsed with invalid date."""
        mock_parse_date.return_value = None
        
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            release_date="invalid-date"
        )
        
        result = episode.get_release_date_parsed()
        assert result is None
    
    def test_get_release_date_parsed_no_date(self):
        """Test get_release_date_parsed when no release date."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3"
        )
        
        result = episode.get_release_date_parsed()
        assert result is None
    
    @patch('fazztv.utils.datetime.calculate_days_old')
    def test_calculate_days_old_with_release_date(self, mock_calc_days):
        """Test calculate_days_old with release date."""
        mock_calc_days.return_value = 30
        
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            release_date="2024-01-15"
        )
        
        days = episode.calculate_days_old()
        assert days == 30
        mock_calc_days.assert_called_once_with("2024-01-15")
    
    @patch('fazztv.utils.datetime.calculate_days_old')
    def test_calculate_days_old_from_title(self, mock_calc_days):
        """Test calculate_days_old extracting date from title."""
        mock_calc_days.return_value = 15
        
        episode = Episode(
            title="My Song - January 15 2024",
            music_url="https://example.com/music.mp3"
        )
        
        days = episode.calculate_days_old()
        assert days == 15
        mock_calc_days.assert_called_once_with("January 15 2024")
    
    @patch('fazztv.utils.datetime.calculate_days_old')
    def test_calculate_days_old_no_date(self, mock_calc_days):
        """Test calculate_days_old when no date available."""
        episode = Episode(
            title="My Song",
            music_url="https://example.com/music.mp3"
        )
        
        days = episode.calculate_days_old()
        assert days == 0
        mock_calc_days.assert_not_called()
    
    def test_str_method(self):
        """Test __str__ method."""
        episode = Episode(
            title="Test Episode",
            music_url="https://example.com/music.mp3",
            guid="12345678-1234-1234-1234-123456789012"
        )
        
        result = str(episode)
        assert "Episode: Test Episode" in result
        assert "GUID: 12345678..." in result
    
    def test_repr_method(self):
        """Test __repr__ method."""
        episode = Episode(
            title="A Very Long Episode Title That Should Be Truncated",
            music_url="https://example.com/music.mp3",
            guid="12345678-1234-1234-1234-123456789012",
            war_title="A Long War Title That Should Also Be Truncated"
        )
        
        result = repr(episode)
        assert "Episode(" in result
        assert "title='A Very Long Episode Title That...'" in result
        assert "guid='12345678...'" in result
        assert "war_title='A Long War Title Tha...'" in result
    
    def test_repr_method_no_war_title(self):
        """Test __repr__ method when war_title is None."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            guid="12345678-1234-1234-1234-123456789012"
        )
        
        result = repr(episode)
        assert "war_title='None...'" in result


class TestEpisodeMetadata:
    """Test Episode metadata operations."""
    
    def test_update_metadata(self):
        """Test updating metadata."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3"
        )
        
        episode.update_metadata("views", 1000)
        
        assert episode.metadata["views"] == 1000
        assert "last_updated" in episode.metadata
        assert episode.metadata["last_updated"] is not None
    
    def test_update_metadata_overwrites(self):
        """Test that update_metadata overwrites existing values."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            metadata={"views": 500}
        )
        
        episode.update_metadata("views", 1500)
        
        assert episode.metadata["views"] == 1500
    
    def test_get_metadata_existing_key(self):
        """Test getting existing metadata value."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3",
            metadata={"key": "value"}
        )
        
        result = episode.get_metadata("key")
        assert result == "value"
    
    def test_get_metadata_missing_key(self):
        """Test getting metadata with missing key returns None."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3"
        )
        
        result = episode.get_metadata("missing")
        assert result is None
    
    def test_get_metadata_with_default(self):
        """Test getting metadata with default value."""
        episode = Episode(
            title="Test",
            music_url="https://example.com/music.mp3"
        )
        
        result = episode.get_metadata("missing", "default_value")
        assert result == "default_value"
    
    def test_metadata_isolation(self):
        """Test that metadata is isolated between instances."""
        episode1 = Episode(
            title="Episode 1",
            music_url="https://example.com/music1.mp3"
        )
        episode2 = Episode(
            title="Episode 2",
            music_url="https://example.com/music2.mp3"
        )
        
        episode1.update_metadata("key", "value1")
        episode2.update_metadata("key", "value2")
        
        assert episode1.metadata["key"] == "value1"
        assert episode2.metadata["key"] == "value2"


class TestEpisodeSerialization:
    """Test Episode serialization methods."""
    
    def test_to_dict(self):
        """Test converting Episode to dictionary."""
        metadata = {"views": 1000, "likes": 50}
        episode = Episode(
            title="Test Episode",
            music_url="https://example.com/music.mp3",
            guid="test-guid",
            war_title="War Title",
            war_url="https://example.com/war.mp4",
            commentary="Test commentary",
            alternative_music_url="https://example.com/alt.mp3",
            release_date="2024-01-15",
            metadata=metadata
        )
        
        data = episode.to_dict()
        
        assert data["title"] == "Test Episode"
        assert data["music_url"] == "https://example.com/music.mp3"
        assert data["guid"] == "test-guid"
        assert data["war_title"] == "War Title"
        assert data["war_url"] == "https://example.com/war.mp4"
        assert data["commentary"] == "Test commentary"
        assert data["alternative_music_url"] == "https://example.com/alt.mp3"
        assert data["release_date"] == "2024-01-15"
        assert data["metadata"] == metadata
    
    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        episode = Episode(
            title="Minimal",
            music_url="https://example.com/music.mp3"
        )
        
        data = episode.to_dict()
        
        assert data["title"] == "Minimal"
        assert data["music_url"] == "https://example.com/music.mp3"
        assert data["guid"] is not None
        assert data["war_title"] is None
        assert data["war_url"] is None
        assert data["commentary"] is None
        assert data["alternative_music_url"] is None
        assert data["release_date"] is None
        assert data["metadata"] == {}
    
    def test_from_dict(self):
        """Test creating Episode from dictionary."""
        data = {
            "title": "Test Episode",
            "music_url": "https://example.com/music.mp3",
            "guid": "test-guid",
            "war_title": "War Title",
            "war_url": "https://example.com/war.mp4",
            "commentary": "Test commentary",
            "alternative_music_url": "https://example.com/alt.mp3",
            "release_date": "2024-01-15",
            "metadata": {"key": "value"}
        }
        
        episode = Episode.from_dict(data)
        
        assert episode.title == "Test Episode"
        assert episode.music_url == "https://example.com/music.mp3"
        assert episode.guid == "test-guid"
        assert episode.war_title == "War Title"
        assert episode.war_url == "https://example.com/war.mp4"
        assert episode.commentary == "Test commentary"
        assert episode.alternative_music_url == "https://example.com/alt.mp3"
        assert episode.release_date == "2024-01-15"
        assert episode.metadata == {"key": "value"}
    
    def test_from_dict_missing_fields(self):
        """Test from_dict with missing optional fields."""
        data = {
            "title": "Minimal",
            "music_url": "https://example.com/music.mp3"
        }
        
        episode = Episode.from_dict(data)
        
        assert episode.title == "Minimal"
        assert episode.music_url == "https://example.com/music.mp3"
        assert episode.guid is not None  # Should generate new GUID
        assert episode.war_title is None
        assert episode.metadata == {}
    
    def test_from_dict_empty_dict(self):
        """Test from_dict with empty dictionary raises validation error."""
        with pytest.raises(ValidationError):
            Episode.from_dict({})
    
    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are inverses."""
        original = Episode(
            title="Roundtrip Test",
            music_url="https://example.com/music.mp3",
            guid="unique-guid",
            war_title="War",
            war_url="https://example.com/war.mp4",
            commentary="Commentary",
            alternative_music_url="https://example.com/alt.mp3",
            release_date="2024-01-15",
            metadata={"test": True, "count": 42}
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Episode.from_dict(data)
        
        # Compare all fields
        assert restored.title == original.title
        assert restored.music_url == original.music_url
        assert restored.guid == original.guid
        assert restored.war_title == original.war_title
        assert restored.war_url == original.war_url
        assert restored.commentary == original.commentary
        assert restored.alternative_music_url == original.alternative_music_url
        assert restored.release_date == original.release_date
        assert restored.metadata == original.metadata
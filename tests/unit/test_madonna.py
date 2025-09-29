"""Comprehensive unit tests for madonna module."""

import json
import os
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, date
import pytest

from fazztv.madonna import (
    load_madonna_data,
    get_madonna_song_url,
    calculate_days_old,
    prepare_overlay_texts,
    setup_environment,
    parse_arguments,
    load_episodes
)


class TestMadonna:
    """Test suite for madonna module."""

    def test_module_imports(self):
        """Test that module can be imported."""
        import fazztv.madonna
        assert fazztv.madonna is not None

    @patch('fazztv.madonna.open', new_callable=mock_open, read_data='{"episodes": [{"title": "Test Episode"}]}')
    @patch('fazztv.madonna.ensure_guid')
    def test_load_madonna_data(self, mock_ensure_guid, mock_file):
        """Test loading Madonna data from JSON file."""
        mock_ensure_guid.return_value = "test-guid-123"

        result = load_madonna_data()

        assert 'episodes' in result
        assert len(result['episodes']) == 1
        assert result['episodes'][0]['title'] == "Test Episode"

    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_success(self, mock_yt_dlp):
        """Test successful YouTube URL retrieval for Madonna song."""
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {
            'entries': [
                {'title': 'Madonna - Like a Prayer', 'webpage_url': 'https://youtube.com/watch?v=abc123'}
            ]
        }
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

        result = get_madonna_song_url("Like a Prayer")

        assert result == 'https://youtube.com/watch?v=abc123'
        mock_ydl_instance.extract_info.assert_called_once()

    @patch('fazztv.madonna.yt_dlp.YoutubeDL')
    def test_get_madonna_song_url_no_results(self, mock_yt_dlp):
        """Test YouTube search returning no results."""
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {'entries': []}
        mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

        result = get_madonna_song_url("Nonexistent Song")

        assert result is None

    def test_calculate_days_old_valid_date(self):
        """Test calculating days since release date."""
        song_info = "Material Girl - November 30 1984"

        days = calculate_days_old(song_info)

        # Calculate expected days
        release_date = datetime(1984, 11, 30)
        expected_days = (datetime.now() - release_date).days

        assert abs(days - expected_days) <= 1  # Allow 1 day tolerance

    def test_calculate_days_old_invalid_date(self):
        """Test calculating days with invalid date format."""
        song_info = "Material Girl - Invalid Date"

        days = calculate_days_old(song_info)

        assert days == 0  # Default value when date not found

    def test_prepare_overlay_texts(self):
        """Test preparing overlay texts for video."""
        episode = {
            'title': 'Like a Prayer - March 3 1989',
            'war_title': 'World War II: The Battle of Britain',
            'commentary': 'Classic Madonna hit: groundbreaking video'
        }

        result = prepare_overlay_texts(episode, 'Like a Prayer')

        assert 'title_text' in result
        assert 'war_text' in result
        assert 'commentary' in result
        assert 'age_text1' in result
        assert 'age_text2' in result
        assert 'Like a Prayer' in result['age_text1']

    @patch('fazztv.madonna.print_banner')
    @patch('fazztv.madonna.cleanup_environment')
    def test_setup_environment(self, mock_cleanup, mock_banner):
        """Test environment setup."""
        setup_environment(dev_mode=True)

        mock_banner.assert_called_once_with('full')
        mock_cleanup.assert_called_once()

    @patch('sys.argv', ['madonna.py', '--dev', '--guids', 'guid1', 'guid2'])
    def test_parse_arguments_with_options(self):
        """Test parsing command line arguments."""
        args = parse_arguments()

        assert args.dev is True
        assert args.guids == ['guid1', 'guid2']

    @patch('sys.argv', ['madonna.py'])
    def test_parse_arguments_defaults(self):
        """Test parsing arguments with defaults."""
        args = parse_arguments()

        assert args.dev is False
        assert args.guids == ["40a441fd-4ce8-49b2-82c4-356f8f13b8c5"]

    @patch('fazztv.madonna.load_madonna_data')
    def test_load_episodes_success(self, mock_load_data):
        """Test loading episodes successfully."""
        mock_load_data.return_value = {
            'episodes': [
                {'title': 'Episode 1'},
                {'title': 'Episode 2'}
            ]
        }

        episodes = load_episodes()

        assert len(episodes) == 2
        assert episodes[0]['title'] == 'Episode 1'

    @patch('fazztv.madonna.load_madonna_data')
    @patch('sys.exit')
    def test_load_episodes_no_data(self, mock_exit, mock_load_data):
        """Test loading episodes with no data."""
        mock_load_data.return_value = {'episodes': []}

        load_episodes()

        mock_exit.assert_called_once_with(1)

"""
Madonna Military History FazzTV Module

This module provides functionality for creating video content that combines Madonna songs
with historical military content. It handles downloading, processing, and broadcasting
of multimedia content with overlay text and effects.

Main Features:
    - Download audio/video content from YouTube
    - Process media with FFmpeg (overlays, effects, transitions)
    - Generate educational content combining music and history
    - Broadcast to RTMP endpoints
    - Cache management for downloaded content

Usage:
    python madonna.py --guids <guid1> <guid2> --dev
"""

import argparse
import shutil
import sys
from datetime import date, datetime
import random
import os
from typing import Optional, List, Tuple, Dict
from loguru import logger
import json
import re
import uuid
import tempfile
import yt_dlp
from fazztv.models import MediaItem
from fazztv.broadcaster import RTMPBroadcaster
from fazztv.utils.ascii_art import print_banner
from fazztv.utils.download_utils import (
    get_cached_file, cache_file, get_yt_dlp_audio_options, get_yt_dlp_video_options,
    find_downloaded_audio_file, move_audio_to_output, prepare_output_directory,
    prepare_base_output_path, download_with_yt_dlp
)
from fazztv.core.error_handling import handle_errors
from fazztv.utils.error_handling import safe_execute
from fazztv.utils.ffmpeg_utils import (
    build_ffmpeg_inputs, build_ffmpeg_filter, build_ffmpeg_command, execute_ffmpeg_command
)
from fazztv.config import constants
from fazztv.utils.guid_utils import ensure_guid
from fazztv.utils.episode_utils import (
    extract_song_name, validate_episode_data, sanitize_text_for_overlay,
    get_episode_defaults, validate_media_file, get_alternative_url
)
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ---------------------------------------------------------------------------
#                           CONFIGURATION
# ---------------------------------------------------------------------------
STREAM_KEY = None
SEARCH_LIMIT = constants.SEARCH_LIMIT
LOG_FILE = constants.MADONNA_LOG_FILE

BASE_RES = constants.BASE_RESOLUTION
FADE_LENGTH = constants.DEFAULT_FADE_LENGTH
MARQUEE_DURATION = constants.MARQUEE_DURATION
SCROLL_SPEED = constants.SCROLL_SPEED
ELAPSED_TUNE_SECONDS = constants.ELAPSED_TUNE_SECONDS

DEFAULT_VIDEO = constants.DEFAULT_VIDEO_FILE

# Path to the JSON data file
DATA_FILE = os.path.join(os.path.dirname(__file__), "madonna_data.json")

# Cache directory for downloaded media files
TEMP_DIR = os.path.join("/tmp", "fazztv")
DEV_MODE = True  # Default to dev mode
DEFAULT_GUID = "e8f7a12b-3c1d-4f3a-9e8d-2b6c7a8d9e0f"

logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

# ---------------------------------------------------------------------------
#                       HELPER FUNCTIONS
# ---------------------------------------------------------------------------

@handle_errors(operation="load_episodes_data", component="madonna", return_value={"episodes": []})
def load_madonna_data() -> Dict[str, List[dict]]:
    """Load Madonna and war documentary data from JSON file."""
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    # Add GUIDs to episodes that don't have them
    modified = False
    for episode in data['episodes']:
        if 'guid' not in episode:
            ensure_guid(episode)
            modified = True

    # Save the updated data if any GUIDs were added
    if modified:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Added GUIDs to episodes in {DATA_FILE}")

    logger.info(f"Successfully loaded {len(data['episodes'])} episodes from {DATA_FILE}")
    return data

def get_madonna_song_url(song_name: str) -> Optional[str]:
    """Search for a Madonna song on YouTube."""
    logger.debug(f"Searching for Madonna song: {song_name}...")
    query = constants.MADONNA_SEARCH_TEMPLATE.format(song_name=song_name)
    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "max_downloads": SEARCH_LIMIT,
        "nopart": True,
        "no_resume": True,
        "fragment_retries": constants.FRAGMENT_RETRIES_MAX
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{SEARCH_LIMIT}:{query}", download=False)
            vids = info.get("entries", [])
            if not vids:
                logger.error(f"No videos found for Madonna - {song_name}")
                return None
            pick = random.choice(vids)
            logger.info(f"Selected for Madonna - {song_name}: {pick['title']} ({pick['webpage_url']})")
            return pick["webpage_url"]
    except Exception as e:
        logger.error(f"Error searching Madonna - {song_name}: {e}")
        return None

# Note: Utility functions moved to fazztv.utils.download_utils

@handle_errors(operation="download_audio_only", component="madonna", return_value=False)
def download_audio_only(url: str, output_file: str, guid: str | None = None) -> bool:
    """Download only the audio from a YouTube video."""
    # Try to use cached version
    if get_cached_file(guid, output_file, TEMP_DIR, 'audio'):
        return True

    logger.debug(f"Downloading audio from {url} to {output_file}")

    # Prepare output directory
    if not prepare_output_directory(output_file):
        return False

    # Create base output path without extension
    base_output = prepare_base_output_path(output_file)

    # Get yt-dlp options
    yt_dlp_opts = get_yt_dlp_audio_options(base_output)

    # Download audio
    if not download_with_yt_dlp(url, yt_dlp_opts, "audio download"):
        return False

    # Find the downloaded file
    found_file = find_downloaded_audio_file(base_output)

    if not found_file:
        logger.error(f"No valid audio file found for {base_output}")
        return False

    # Move to expected location
    if not move_audio_to_output(found_file, output_file):
        return False

    # Cache for future use
    cache_file(output_file, guid, TEMP_DIR, 'audio')

    return True

def calculate_days_old(song_info: str) -> int:
    """Calculate days since release date in song info."""
    date_match = re.search(r'- ([A-Za-z]+ \d{1,2} \d{4})$', song_info)
    if date_match:
        reference_date = datetime.strptime(date_match.group(1), '%B %d %Y').date()
        days_old = (date.today() - reference_date).days
        return days_old
    return 0

@handle_errors(operation="download_video_only", component="madonna", return_value=False)
def download_video_only(url: str, output_file: str, guid: str | None = None) -> bool:
    """Download only the video from a YouTube video."""
    # Check if cached file exists
    if get_cached_file(guid, output_file, TEMP_DIR, 'video'):
        return True

    logger.debug(f"Downloading video from {url} to {output_file}")
    ydl_opts = get_yt_dlp_video_options(output_file)

    # Download video
    if not download_with_yt_dlp(url, ydl_opts, "video download"):
        return False

    # Cache the file if guid is provided and download was successful
    cache_file(output_file, guid, TEMP_DIR, 'video')

    return True

@handle_errors(operation="cleanup_environment", component="madonna", return_value=None)
def cleanup_environment() -> None:
    """Prepare environment without purging cached files."""
    # Clear pycache if in dev mode.
    if DEV_MODE:
        pycache_dir = os.path.join(os.path.dirname(__file__), "__pycache__")
        if os.path.exists(pycache_dir):
            safe_execute(
                shutil.rmtree,
                args=(pycache_dir,),
                operation_name="clear pycache directory"
            )
            logger.info("Cleared __pycache__ directory")

    # Ensure temp directory exists (do not purge it to enable caching).
    safe_execute(
        os.makedirs,
        args=(TEMP_DIR,),
        kwargs={"exist_ok": True},
        operation_name="create temp directory"
    )
    logger.info(f"Using temp directory: {TEMP_DIR}")


def prepare_overlay_texts(episode: dict, song_name: str) -> Dict[str, str]:
    """Prepare text overlays for the video."""
    episode = get_episode_defaults(episode)
    title_text = sanitize_text_for_overlay(episode['title'])

    # Handle optional war_title field
    war_title = episode['war_title']
    war_text = sanitize_text_for_overlay(war_title)
    war_topic = sanitize_text_for_overlay(war_title.split(':')[0])

    # Handle optional commentary field
    commentary = episode['commentary']
    commentary_text = sanitize_text_for_overlay(commentary.split(':')[0])

    age_days = '{:,}'.format(calculate_days_old(episode['title']))
    age_text1 = (f"Madonnas {song_name} is {age_days} days old today -")
    age_text2 = (f"so ancient its release date was closer in history to the {war_topic}!")

    return {
        'title_text': title_text,
        'war_text': war_text,
        'commentary': commentary_text,
        'age_text1': age_text1,
        'age_text2': age_text2
    }


# Note: FFmpeg utility functions moved to fazztv.utils.ffmpeg_utils






# Note: _build_ffmpeg_command moved to fazztv.utils.ffmpeg_utils


@handle_errors(operation="create_media_item", component="madonna", return_value=None)
def create_media_item_from_episode(episode: dict) -> MediaItem | None:
    """Create a MediaItem from an episode in the JSON data."""
    logger.info(f"Creating media item for '{episode['title']}'")

    # Extract song name from title
    song_name = extract_song_name(episode['title'])

    # Ensure GUID exists
    guid = ensure_guid(episode)

    texts = prepare_overlay_texts(episode, song_name)

    fztv_logo_exists = os.path.exists(constants.DEFAULT_LOGO_FILE)

    # Build FFmpeg inputs
    input_args = build_ffmpeg_inputs(episode)

    # Build filter complex
    filter_complex, marquee_text = build_ffmpeg_filter(texts, fztv_logo_exists)

    # Add marquee and optional logo inputs
    input_args.extend(["-f", "lavfi", "-i", marquee_text])
    if fztv_logo_exists:
        input_args.extend(["-i", constants.DEFAULT_LOGO_FILE])

    output_file = os.path.join(TEMP_DIR, f"{guid}{constants.OUTPUT_CACHE_SUFFIX}")
    cmd = build_ffmpeg_command(input_args, filter_complex, output_file, ELAPSED_TUNE_SECONDS)

    if not execute_ffmpeg_command(cmd, f"FFmpeg processing for episode '{episode['title']}'"):
        logger.error(f"FFmpeg processing failed for episode '{episode['title']}'")
        raise RuntimeError("FFmpeg processing failed")

    # Use music_url from episode data, or empty string if not available
    music_url = episode.get('music_url', '')

    media_item = MediaItem(
        artist="Madonna",
        song=song_name,
        url=music_url,
        taxprompt=episode.get('commentary', ''),
        length_percent=100,
        duration=ELAPSED_TUNE_SECONDS
    )
    media_item.serialized = output_file
    return media_item

def setup_environment(dev_mode: bool = False) -> None:
    global DEV_MODE
    DEV_MODE = dev_mode
    print_banner('full')
    cleanup_environment()
    logger.info("=== Starting Madonna Military History FazzTV broadcast ===")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Madonna Military History FazzTV broadcast')
    parser.add_argument('--guids', nargs='*', help='List of GUIDs to process',
                        default=["40a441fd-4ce8-49b2-82c4-356f8f13b8c5"])
    parser.add_argument('--dev', action='store_true', help='Run in development mode', default=False)
    return parser.parse_args()


def load_episodes() -> List[dict]:
    data = load_madonna_data()
    episodes = data.get('episodes')
    if not episodes:
        logger.error("No matching episodes found for provided GUIDs")
        sys.exit(1)
    return episodes


@handle_errors(operation="process_episode_audio", component="madonna", return_value=False)
def process_episode_audio(episode: dict, temp_dir: str) -> bool:
    guid = episode.get('guid')
    audio_path = os.path.join(temp_dir, f"madonna_audio_{guid}.aac")

    if not episode.get("audio_file", "").strip():
        logger.debug(f"Attempting to download/retrieve audio for {episode['title']} (GUID: {guid})")
        if not download_audio_only(episode['music_url'], audio_path, guid):
            logger.error(f"Failed to download audio for {episode['title']}")
            if episode.get('alternative_music_url'):
                logger.info(f"Trying alternative music URL for {episode['title']}")
                if not download_audio_only(episode['alternative_music_url'], audio_path, guid):
                    logger.error(f"Failed to download audio from alternative URL for {episode['title']}")
                    return False
            else:
                return False
        if not validate_media_file(audio_path):
            logger.error(f"Audio file is missing or empty: {audio_path}")
            return False
        logger.debug(f"Successfully obtained audio at {audio_path}")
        episode["audio_file"] = audio_path
    return True


@handle_errors(operation="process_episode_video", component="madonna", return_value=False)
def process_episode_video(episode: dict, temp_dir: str) -> bool:
    guid = episode.get('guid')
    video_path = os.path.join(temp_dir, f"madonna_video_{guid}.mp4")

    if not episode.get("video_file", "").strip():
        if episode.get("video_url", "").strip():
            logger.debug(f"Attempting to download/retrieve video for {episode['title']} (GUID: {guid})")
            if not download_video_only(episode['video_url'], video_path, guid):
                logger.error(f"Failed to download video for {episode['title']}")
                if os.path.exists(DEFAULT_VIDEO):
                    episode["video_file"] = DEFAULT_VIDEO
                else:
                    return False
            else:
                if not validate_media_file(video_path):
                    logger.error(f"Video file is missing or empty: {video_path}")
                    return False
                logger.debug(f"Successfully obtained video at {video_path}")
                episode["video_file"] = video_path
        elif os.path.exists(DEFAULT_VIDEO):
            episode["video_file"] = DEFAULT_VIDEO
        else:
            episode["video_file"] = ""
    return True


@handle_errors(operation="process_episodes", component="madonna", return_value=[])
def process_episodes(episodes: List[dict]) -> List[MediaItem]:
    media_items = []
    temp_dir = os.path.join(tempfile.gettempdir(), "fazztv")

    for episode in episodes:
        guid = ensure_guid(episode)

        if not process_episode_audio(episode, temp_dir):
            continue

        if not process_episode_video(episode, temp_dir):
            continue

        media_item = create_media_item_from_episode(episode)
        if media_item:
            media_items.append(media_item)

    logger.info(f"Created {len(media_items)} media items")
    return media_items


def broadcast_media(media_items: List[MediaItem], rtmp_url: str) -> List[Tuple[MediaItem, bool]]:
    broadcaster = RTMPBroadcaster(rtmp_url=rtmp_url)
    results = []

    for item in media_items:
        success = broadcaster.broadcast_item(item)
        results.append((item, success))

    successful_count = sum(1 for _, success in results if success)
    logger.info(f"Broadcast {successful_count} media items successfully")
    return results


def main() -> None:
    args = parse_arguments()
    setup_environment(args.dev)
    episodes = load_episodes()

    rtmp_url = constants.get_rtmp_url(STREAM_KEY)

    media_items = process_episodes(episodes)

    if media_items:
        broadcast_media(media_items, rtmp_url)
    logger.info("=== Finished Madonna Military History FazzTV broadcast ===")


if __name__ == "__main__":
    main()
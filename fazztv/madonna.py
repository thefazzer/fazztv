import random
import time
import os
import requests
from loguru import logger
import json
import subprocess
import tempfile
from typing import List, Optional, Tuple
import re

from fazztv.models import MediaItem
from fazztv.serializer import MediaSerializer
from fazztv.broadcaster import RTMPBroadcaster
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ---------------------------------------------------------------------------
#                           CONFIGURATION
# ---------------------------------------------------------------------------
STREAM_KEY = None
SEARCH_LIMIT = 5
LOG_FILE = "madonna_broadcast.log"

BASE_RES = "640x360"
FADE_LENGTH = 3
MARQUEE_DURATION = 86400
SCROLL_SPEED = 40

# Path to the JSON data file
DATA_FILE = os.path.join(os.path.dirname(__file__), "madonna_data.json")

logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

# ---------------------------------------------------------------------------
#                       HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def load_madonna_data():
    """Load Madonna and war documentary data from JSON file."""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {len(data['episodes'])} episodes from {DATA_FILE}")
        return data
    except Exception as e:
        logger.error(f"Error loading data from {DATA_FILE}: {e}")
        return {"episodes": []}

def get_madonna_song_url(song_name):
    """Search for a Madonna song on YouTube."""
    logger.debug(f"Searching for Madonna song: {song_name}...")
    import yt_dlp
    query = f"Madonna {song_name} official music video"
    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "max_downloads": SEARCH_LIMIT,
        "nopart": True,
        "no_resume": True,
        "fragment_retries": 999
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

def download_audio_only(url, output_file):
    """Download only the audio from a YouTube video."""
    logger.debug(f"Downloading audio from {url} to {output_file}")
    import yt_dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_file,
        "quiet": True,
        "overwrites": True,
        "continuedl": False,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "aac",
            "preferredquality": "192",
        }]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return False

def download_video_only(url, output_file):
    """Download only the video from a YouTube video."""
    logger.debug(f"Downloading video from {url} to {output_file}")
    import yt_dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]",
        "outtmpl": output_file,
        "quiet": True,
        "overwrites": True,
        "continuedl": False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False

def combine_audio_video(audio_file, video_file, output_file, song_info, war_info, documentary_title):
    """Combine audio from Madonna song with video from war documentary."""
    logger.debug(f"Combining {audio_file} and {video_file} to {output_file}")
    
    # Create temporary files for the text content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as song_file:
        song_path = song_file.name
        song_file.write(song_info)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as war_file:
        war_path = war_file.name
        war_file.write(war_info)
    
    # Check if logo exists
    logo_exists = os.path.exists("fztv-logo.png")
    if logo_exists:
        logo_input = ["-i", "fztv-logo.png"]
        scale_logo = "[3:v]scale=100:-1[logosize];"
        overlay_logo = "[temp][logosize]overlay=10:10[outv]"
    else:
        logo_input = []
        scale_logo = ""
        overlay_logo = "[temp]copy[outv]"
    
    # Escape single quotes in text
    safe_title = documentary_title.replace("'", "\\'")
    
    # Create filter string
    filter_str = (
        "[0:v]scale=640:360,setsar=1[v0];"
        
        # Add title overlay
        "[v0]drawtext=text='" + safe_title + "':"
        "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
        "fontsize=24:fontcolor=cyan:bordercolor=green:borderw=2:"
        "x=(w-text_w)/2:y=15:enable=1[titled];"
        
        # Add song info overlay
        "[titled]drawtext=textfile=" + song_path + ":"
        "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
        "fontsize=10:fontcolor=black:bordercolor=green:borderw=1:"
        "x=(w-text_w)/2:y=35:enable=1[titledbylined];"
        
        # Add marquee
        "[2:v]scale=640:100[marq];"
        "[titledbylined][marq]overlay=0:360-100[temp];"
        
        # Add logo
        f"{scale_logo}"
        f"{overlay_logo}"
    )
    
    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-f", "lavfi",
        "-i", (
            f"color=c=black:s=1280x100:d={MARQUEE_DURATION},"
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            f"textfile={war_path}:"
            "fontsize=16:"
            "fontcolor=white:"
            "y=10:"
            f"x='1280 - mod(t*{SCROLL_SPEED}, 1280+text_w)':"
            "enable=1"
        )
    ] + logo_input + [
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-r", "30", "-vsync", "2",
        "-movflags", "+faststart",
        output_file
    ]
    
    # Run FFmpeg
    logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr.decode('utf-8', 'ignore')}")
            return False
        return True
    except Exception as e:
        logger.error(f"FFmpeg exception: {e}")
        return False
    finally:
        # Clean up temporary files
        if os.path.exists(song_path):
            os.remove(song_path)
        if os.path.exists(war_path):
            os.remove(war_path)

def create_media_item_from_episode(episode):
    """Create a MediaItem from an episode in the JSON data."""
    logger.info(f"Creating media item for '{episode['title']}'")
    
    # Extract song name from title
    song_match = re.match(r"^(.*?)\s*\(", episode['title'])
    song_name = song_match.group(1) if song_match else "Unknown Song"
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.aac', delete=False) as audio_file:
        audio_path = audio_file.name
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
        video_path = video_file.name
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # Download audio from Madonna song
        if not download_audio_only(episode['music_url'], audio_path):
            logger.error(f"Failed to download audio for {episode['title']}")
            return None
        
        # Download video from war documentary
        war_url = episode['war_url'] if episode['war_url'] else "https://www.youtube.com/watch?v=8a8fqGpHgsk"
        if not download_video_only(war_url, video_path):
            logger.error(f"Failed to download video for {episode['war_title']}")
            return None
        
        # Combine audio and video
        if not combine_audio_video(audio_path, video_path, output_path, episode['title'], episode['commentary'], episode['war_title']):
            logger.error(f"Failed to combine audio and video for {episode['title']}")
            return None
        
        # Create MediaItem
        try:
            media_item = MediaItem(
                artist="Madonna",
                song=song_name,
                url=episode['music_url'],
                taxprompt=episode['commentary'],
                length_percent=100
            )
            # Set the serialized path directly
            media_item.serialized = output_path
            return media_item
        except ValueError as e:
            logger.error(f"Error creating MediaItem: {e}")
            return None
    except Exception as e:
        logger.error(f"Error in create_media_item: {e}")
        return None
    finally:
        # We don't delete the files here as they're needed for broadcasting
        pass

def main():
    logger.info("=== Starting Madonna Military History FazzTV broadcast ===")
    
    # Load data from JSON
    data = load_madonna_data()
    
    # Create broadcaster
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}" if STREAM_KEY else "rtmp://127.0.0.1:1935/live/test"
    broadcaster = RTMPBroadcaster(rtmp_url=rtmp_url)
    
    # Create a collection of media items
    media_items = []
    
    # Shuffle episodes
    episodes = data.get('episodes', [])
    random.shuffle(episodes)
    
    # Create media items from episodes
    for episode in episodes:
        media_item = create_media_item_from_episode(episode)
        if media_item:
            media_items.append(media_item)
    
    logger.info(f"Created {len(media_items)} media items")
    
    # Broadcast the media items
    results = []
    for item in media_items:
        success = broadcaster.broadcast_item(item)
        results.append((item, success))
        
        # Clean up the serialized file after broadcasting
        if os.path.exists(item.serialized):
            os.remove(item.serialized)
    
    logger.info(f"Broadcast {sum(1 for _, success in results if success)} media items successfully")
    logger.info("=== Finished Madonna Military History FazzTV broadcast ===")

if __name__ == "__main__":
    main()
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
    
    # Get the directory path and ensure it exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create a base output without any extension
    base_output = os.path.splitext(output_file)[0]
    if base_output.endswith('.aac'):
        base_output = base_output[:-4]  # Remove .aac if it's still there
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{base_output}.%(ext)s",  # Let yt-dlp handle the extension
        "quiet": False,
        "verbose": True,
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
            info = ydl.extract_info(url, download=True)
            if not info:
                logger.error(f"No information extracted for URL: {url}")
                return False
        
        # Check for possible file extensions that yt-dlp might have created
        possible_extensions = ['.aac', '.m4a', '.aac.m4a', '.aac.mp4', '.mp3']
        found_file = None
        
        for ext in possible_extensions:
            potential_file = f"{base_output}{ext}"
            if os.path.exists(potential_file) and os.path.getsize(potential_file) > 0:
                found_file = potential_file
                logger.debug(f"Found audio file: {found_file} ({os.path.getsize(found_file)} bytes)")
                break
        
        if found_file:
            # Rename to the expected output file
            if found_file != output_file:
                logger.debug(f"Renaming {found_file} to {output_file}")
                if os.path.exists(output_file):
                    os.remove(output_file)
                os.rename(found_file, output_file)
            return True
        else:
            # Try a more aggressive search in the directory
            dir_path = os.path.dirname(base_output)
            base_name = os.path.basename(base_output)
            logger.debug(f"Searching directory {dir_path} for files starting with {base_name}")
            
            for file in os.listdir(dir_path):
                if file.startswith(os.path.basename(base_name)) and os.path.getsize(os.path.join(dir_path, file)) > 0:
                    found_file = os.path.join(dir_path, file)
                    logger.debug(f"Found alternative audio file: {found_file}")
                    if os.path.exists(output_file):
                        os.remove(output_file)
                    os.rename(found_file, output_file)
                    return True
            
            logger.error(f"No valid audio file found for {base_output} with any expected extension")
            return False
            
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
    
    # Check if logos exist
    logo1_exists = os.path.exists("fztv-logo.png")
    logo2_exists = os.path.exists("logo-madmil.png")
    
    logo_inputs = []
    scale_logo1, overlay_logo1 = "", ""
    scale_logo2, overlay_logo2 = ""
    
    if logo1_exists:
        logo_inputs += ["-i", "fztv-logo.png"]
        scale_logo1 = "[3:v]scale=100:-1[logosize1];"
        overlay_logo1 = "[temp][logosize1]overlay=10:10[with_logo1];"
    else:
        overlay_logo1 = "[temp]copy[with_logo1];"
    
    if logo2_exists:
        logo_inputs += ["-i", "logo-madmil.png"]
        scale_logo2 = "[4:v]scale=100:-1[logosize2];"
        overlay_logo2 = "[with_logo1][logosize2]overlay=10:50[outv];"
    else:
        overlay_logo2 = "[with_logo1]copy[outv];"
    
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
        
        # Add logos
        f"{scale_logo1}{overlay_logo1}"
        f"{scale_logo2}{overlay_logo2}"
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
    ] + logo_inputs + [
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
    
    # Create temporary files with proper extensions
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"madonna_audio_{int(time.time())}.aac")
    video_path = os.path.join(temp_dir, f"madonna_video_{int(time.time())}.mp4")
    output_path = os.path.join(temp_dir, f"madonna_output_{int(time.time())}.mp4")
    
    try:
        # Download audio from Madonna song
        logger.debug(f"Attempting to download audio from {episode['music_url']} to {audio_path}")
        if not download_audio_only(episode['music_url'], audio_path):
            logger.error(f"Failed to download audio for {episode['title']}")
            # Try an alternative URL if available
            if 'alternative_music_url' in episode and episode['alternative_music_url']:
                logger.info(f"Trying alternative music URL for {episode['title']}")
                if not download_audio_only(episode['alternative_music_url'], audio_path):
                    logger.error(f"Failed to download audio from alternative URL for {episode['title']}")
                    return None
            else:
                return None
        
        # Verify the audio file exists and has content
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            logger.error(f"Audio file is missing or empty: {audio_path}")
            return None
            
        logger.debug(f"Successfully downloaded audio to {audio_path}")
        
        # Download video from war documentary
        war_url = episode['war_url'] if episode['war_url'] else "https://www.youtube.com/watch?v=8a8fqGpHgsk"
        logger.debug(f"Attempting to download video from {war_url} to {video_path}")
        if not download_video_only(war_url, video_path):
            logger.error(f"Failed to download video for {episode['war_title']}")
            return None
            
        # Verify the video file exists and has content
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            logger.error(f"Video file is missing or empty: {video_path}")
            return None
            
        logger.debug(f"Successfully downloaded video to {video_path}")
        
        # Combine audio and video
        logger.debug(f"Combining audio ({audio_path}) and video ({video_path}) to {output_path}")
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
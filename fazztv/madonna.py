import argparse 
import shutil
import sys
from datetime import date, datetime
import random
import time
import os
import requests
from loguru import logger
import json
import subprocess
from typing import List, Optional, Tuple
import re
import uuid
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
ELAPSED_TUNE_SECONDS = 10  # Default duration for media clips in seconds

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

def load_madonna_data():
    """Load Madonna and war documentary data from JSON file."""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Add GUIDs to episodes that don't have them
        modified = False
        for episode in data['episodes']:
            if 'guid' not in episode:
                episode['guid'] = str(uuid.uuid4())
                modified = True
        
        # Save the updated data if any GUIDs were added
        if modified:
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Added GUIDs to episodes in {DATA_FILE}")
        
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

def download_audio_only(url, output_file, guid=None):
    """Download only the audio from a YouTube video."""
    # Check if cached file exists
    if guid:
        cached_file = os.path.join(TEMP_DIR, f"{guid}_audio.aac")
        if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
            logger.info(f"Using cached audio file for GUID {guid}")
            shutil.copy(cached_file, output_file)
            return True
    
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
    
    yt_dlp_opts = {
        "format": "bestaudio/best",
        "max_duration": ELAPSED_TUNE_SECONDS,
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
        with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
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
            
            # Cache the file if guid is provided
            if guid:
                cached_file = os.path.join(TEMP_DIR, f"{guid}_audio.aac")
                logger.debug(f"Caching audio file to {cached_file}")
                shutil.copy(output_file, cached_file)
                
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
                    
                    # Cache the file if guid is provided
                    if guid:
                        cached_file = os.path.join(TEMP_DIR, f"{guid}_audio.aac")
                        logger.debug(f"Caching audio file to {cached_file}")
                        shutil.copy(output_file, cached_file)
                        
                    return True
            
            logger.error(f"No valid audio file found for {base_output} with any expected extension")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return False

def calculate_days_old(song_info: str) -> int:
        date_match = re.search(r'- ([A-Za-z]+ \d{1,2} \d{4})$', song_info)
        if date_match:
            reference_date = datetime.strptime(date_match.group(1), '%B %d %Y').date()
            days_old = (date.today() - reference_date).days
            return days_old
        return 0

def download_video_only(url, output_file, guid=None):
    """Download only the video from a YouTube video."""
    # Check if cached file exists
    if guid:
        cached_file = os.path.join(TEMP_DIR, f"{guid}_video.mp4")
        if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
            logger.info(f"Using cached video file for GUID {guid}")
            shutil.copy(cached_file, output_file)
            return True
    
    logger.debug(f"Downloading video from {url} to {output_file}")
    import yt_dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]",
        "max_duration": ELAPSED_TUNE_SECONDS,
        "outtmpl": output_file,
        "quiet": True,
        "overwrites": True,
        "continuedl": False,
        "cookiesfrombrowser": ("chrome",),  # Add this line to use Chrome cookies
        "age_limit": 99  # Allow age-restricted content
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Cache the file if guid is provided and download was successful
        if guid and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            cached_file = os.path.join(TEMP_DIR, f"{guid}_video.mp4")
            logger.debug(f"Caching video file to {cached_file}")
            shutil.copy(output_file, cached_file)
            
        return True
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False

def create_media_item_from_episode(episode):
    """Create a MediaItem from an episode in the JSON data."""
    logger.info(f"Creating media item for '{episode['title']}'")
    
    try:
        # Extract song name from title
        song_match = re.match(r"^(.*?)\s*\(", episode['title'])
        song_name = song_match.group(1) if song_match else "Unknown Song"
        
        # Get episode GUID
        guid = episode.get('guid')
        if not guid:
            guid = str(uuid.uuid4())
            episode['guid'] = guid
            logger.info(f"Generated new GUID {guid} for episode '{episode['title']}'")
        

        
        try:
            title_text = episode['title'].replace("'", r"\\'")
            war_text = episode['war_title'].replace("'", r"\\'")
            war_topic = episode['war_title'].split(':')[0].replace("'", r"\\'")
            commentary = episode['commentary'].split(':')[0].replace("'", r"\\'")
            age_days = '{:,}'.format(calculate_days_old(episode['title']))
            age_text = f"{song_name} is {age_days} days old-so ancient its release date was closer in history to the {war_topic} than to today!"

            # Check for logo
            fztv_logo_exists = os.path.exists("fztv-logo.png")

            # Build input arguments
            input_args = [
                "-f", "lavfi", "-i", "color=c=black:s=2080x1170",  # Black background
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",  # Silent audio
            ]
             # Add marquee
            marquee_text = (
                "color=c=black:s=2080x50,"
                "drawtext='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
                f"text={commentary}:"
                "fontsize=36:fontcolor=white:bordercolor=black:borderw=3:"
                "x=w - mod(40*t\\, w+text_w):"
                "y=h-th-10'"
            )
            
            filter_main = [
                "color=c=black:s=2080x1170[black_col];[3:v]scale=2080:1170:force_original_aspect_ratio=decrease,setsar=1[v0];[black_col][v0]hstack[out_v]",
                f"[out_v]drawtext=text='{war_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=50:fontcolor=red:bordercolor=black:borderw=4:x=(w-text_w)/2:y=30[war_titled]",
                f"[war_titled]drawtext=text='{title_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=40:fontcolor=yellow:bordercolor=black:borderw=4:x=(w-text_w)/2:y=90[titled]",
                 "movie=didyouknow-lightbulb.png[bulb]",
                "[bulb]scale=95:95[scaled_bulb]",
                "[titled][scaled_bulb]overlay=(w/2)+650:120[v2_with_bulb]",
                f"[v2_with_bulb]drawtext=text='{age_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=26:fontcolor=white:bordercolor=black:borderw=3:x=(w-text_w)/2:y=160[titledbylined]"            
            ]

            input_args.extend(["-f", "lavfi", "-i", marquee_text])
            filter_main.extend([
                "[2:v]scale=2080:50[marq]",
                "[titledbylined][marq]overlay=0:main_h-overlay_h-10[outv]"
            ])

            if fztv_logo_exists:
                input_args.extend(["-i", "fztv-logo.png"])
                
            next_input = 3
            last_output = "outv"

            if fztv_logo_exists:
                filter_main.append(f"[{next_input}:v]scale=250:250,setpts=PTS-STARTPTS[fztvlogo]")
                filter_main.append(f"[{last_output}][fztvlogo]overlay=200:0[outfinal]")
            
            filter_complex = ";".join(filter_main)

            output_file = os.path.join(TEMP_DIR, f"{guid}_output.mp4")
            cmd = [
                "ffmpeg", "-y",
                *input_args,
                "-filter_complex", filter_complex,
                "-r", "10",  # set frame rate to 10 fps
                "-map", "[outfinal]",
                "-map", "1:a",
                #"-c:v", "libx264", "-preset", "fast",
                "-c:v", "h264_nvenc", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k",
                "-t", "10",
                output_file
            ]

            subprocess.run(cmd, check=True)
            
            # Create MediaItem
            media_item = MediaItem(
                artist="Madonna",
                song=song_name,
                url="",
                taxprompt=episode['commentary'],
                length_percent=100,
                duration=ELAPSED_TUNE_SECONDS
            )
            media_item.serialized = output_file
            return media_item

        except Exception as e:
            logger.error(f"Error in ffmpeg processing: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error in create_media_item: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
        

def cleanup_environment():
    """Clean up environment before running"""
    # Clear pycache
    if DEV_MODE:
        pycache_dir = os.path.join(os.path.dirname(__file__), "__pycache__")
        if os.path.exists(pycache_dir):
            shutil.rmtree(pycache_dir)
            logger.info("Cleared __pycache__ directory")
    
    # Ensure temp directory exists and is clean
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    logger.info(f"Initialized temp directory: {TEMP_DIR}")

def log_run_details(guids):
    """Log details about the current run"""
    details = {
        "dev_mode": DEV_MODE,
        "guid_count": len(guids),
        "guids": guids,
        "caching_enabled": not DEV_MODE,
        "temp_dir": TEMP_DIR,
        "using_real_video": os.path.exists("madonna-rotator.mp4")
    }
    
    logger.info("=== Run Configuration ===")
    for key, value in details.items():
        logger.info(f"{key}: {value}")
        print(f"{key}: {value}")
    logger.info("======================")

def main():
    parser = argparse.ArgumentParser(description='Madonna Military History FazzTV broadcast')
    parser.add_argument('--guids', nargs='*', help='List of GUIDs to process', 
                       default=[DEFAULT_GUID])
    parser.add_argument('--dev', action='store_true', help='Run in development mode',
                       default=True)
    args = parser.parse_args()
    
    global DEV_MODE
    DEV_MODE = args.dev
    
    # Initialize environment
    cleanup_environment()
    log_run_details(args.guids)
    
    logger.info("=== Starting Madonna Military History FazzTV broadcast ===")
    
    # Load data from JSON
    data = load_madonna_data()
    
    # Filter episodes by provided GUIDs
    episodes = [ep for ep in data.get('episodes', []) 
               if ep.get('guid') in args.guids]
    
    if not episodes:
        logger.error("No matching episodes found for provided GUIDs")
        sys.exit(1)
        
    # Create broadcaster
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}" if STREAM_KEY else "rtmp://127.0.0.1:1935/live/test"
    broadcaster = RTMPBroadcaster(rtmp_url=rtmp_url)
    
    # Create media items from filtered episodes
    media_items = []
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
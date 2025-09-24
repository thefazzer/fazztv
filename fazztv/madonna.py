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
from fazztv.utils.ascii_art import print_banner
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
SCROLL_SPEED = 65
ELAPSED_TUNE_SECONDS = 60  # Default duration for media clips in seconds

DEFAULT_VIDEO = "madonna-rotator.mp4"

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

def cleanup_environment():
    """Prepare environment without purging cached files."""
    # Clear pycache if in dev mode.
    if DEV_MODE:
        pycache_dir = os.path.join(os.path.dirname(__file__), "__pycache__")
        if os.path.exists(pycache_dir):
            shutil.rmtree(pycache_dir)
            logger.info("Cleared __pycache__ directory")
    # Ensure temp directory exists (do not purge it to enable caching).
    os.makedirs(TEMP_DIR, exist_ok=True)
    logger.info(f"Using temp directory: {TEMP_DIR}")


def create_media_item_from_episode(episode):
    """Create a MediaItem from an episode in the JSON data."""
    logger.info(f"Creating media item for '{episode['title']}'")
    try:
        # Extract song name from title.
        song_match = re.match(r"^(.*?)\s*\(", episode['title'])
        song_name = song_match.group(1) if song_match else "Unknown Song"

        # Ensure GUID exists.
        guid = episode.get('guid')
        if not guid:
            guid = str(uuid.uuid4())
            episode['guid'] = guid
            logger.info(f"Generated new GUID {guid} for episode '{episode['title']}'")

        # Prepare overlay texts.
        title_text = episode['title'].replace("'", r"\\'")
        war_text = episode['war_title'].replace("'", r"\\'")
        war_topic = episode['war_title'].split(':')[0].replace("'", r"\\'")
        commentary = episode['commentary'].split(':')[0].replace("'", r"\\'")
        age_days = '{:,}'.format(calculate_days_old(episode['title']))
        age_text1 = (f"Madonnas {song_name} is {age_days} days old today -")
        age_text2 = (f"so ancient its release date was closer in history to the {war_topic}!")

        # Get file paths from episode data.
        video_file = episode.get("video_file", "").strip()
        audio_file = episode.get("audio_file", "").strip()
        
        fztv_logo_exists = os.path.exists("fztv-logo.png")

        # Build input_args with fixed ordering:
        # 0: Black background; 1: Audio; 2: Main video; 3: Marquee; 4: Optional logo.
        input_args = []
        # (0) Black background.
        input_args.extend(["-f", "lavfi", "-i", "color=c=black:s=2080x1170"])
        # (1) Audio: use provided file if exists; else silent audio.
        if audio_file:
            input_args.extend(["-i", audio_file])
        else:
            input_args.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        # (2) Video: use provided file if exists; else default if available; else dummy.
        if video_file:
            input_args.extend(["-i", video_file])
        elif os.path.exists(DEFAULT_VIDEO):
            input_args.extend(["-i", DEFAULT_VIDEO])
        else:
            input_args.extend(["-f", "lavfi", "-i", "nullsrc=s=640x480:d=10:r=30"])
        # (3) Marquee input.
        marquee_text = (
            "color=c=black:s=2080x50,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "text='" + commentary + "':"
            "fontsize=36:fontcolor=white:bordercolor=black:borderw=3:"
            "x=w-mod(40*t\\,w+text_w):"
            "y=h-th-10"
        )
        input_args.extend(["-f", "lavfi", "-i", marquee_text])
        # (4) Optional logo.
        if fztv_logo_exists:
            input_args.extend(["-i", "fztv-logo.png"])

        # Build filter_complex.
        # Input mapping: [0:v]=background, [1:a]=audio, [2:v]=main video, [3:v]=marquee, [4:v]=logo.
        filter_main = [
            # Combine background and main video.
            "[0:v]scale=2080:1170[bg];[2:v]scale=2080:1170[vmain];[bg][vmain]overlay=0:0[base]",
            # War and title text overlays.
            f"[base]drawtext=text='{war_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=50:fontcolor=red:bordercolor=black:borderw=4:x=(w-text_w)/2:y=30[war_titled]",
            f"[war_titled]drawtext=text='{title_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=40:fontcolor=yellow:bordercolor=black:borderw=4:x=(w-text_w)/2:y=90[titled]",
            # Example overlay: a did-you-know lightbulb.
            "movie=didyouknow-lightbulb.png[bulb]",
            "[bulb]scale=95:95[scaled_bulb]",
            "[titled][scaled_bulb]overlay=(W/2)-20:175[v2_with_bulb]",
            # Age text overlay.
            f"[v2_with_bulb]drawtext=text='{age_text1}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=28:fontcolor=white:bordercolor=black:borderw=3:x=(w-text_w)/2:y=280[titledbylined]",
            f"[titledbylined]drawtext=text='{age_text2}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=28:fontcolor=white:bordercolor=black:borderw=3:x=(w-text_w)/2:y=330[titledbylined]",
            # Marquee overlay.
            "[3:v]scale=2080:50[marq]",
            "[titledbylined][marq]overlay=0:main_h-overlay_h-10[with_marq]"
        ]
        if fztv_logo_exists:
            filter_main.append("[4:v]scale=250:250[logo]")
            filter_main.append("[with_marq][logo]overlay=200:0[outfinal]")
        else:
            filter_main.append("[with_marq]copy[outfinal]")
        filter_complex = ";".join(filter_main)

        output_file = os.path.join(TEMP_DIR, f"{guid}_output.mp4")
        cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-r", "10",
            "-map", "[outfinal]",
            "-map", "1:a",
            "-c:v", "h264_nvenc", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-t", f"{ELAPSED_TUNE_SECONDS}",
            output_file
        ]

        subprocess.run(cmd, check=True)

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
        logger.error(f"Error in create_media_item_from_episode: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    
    import tempfile
    import time
    parser = argparse.ArgumentParser(description='Madonna Military History FazzTV broadcast')
    parser.add_argument('--guids', nargs='*', help='List of GUIDs to process', 
                        default=["40a441fd-4ce8-49b2-82c4-356f8f13b8c5"])
    parser.add_argument('--dev', action='store_true', help='Run in development mode', default=False)
    args = parser.parse_args()

    global DEV_MODE
    DEV_MODE = args.dev

    # Display City Driver banner
    print_banner('full')

    # Initialize environment (now reusing TEMP_DIR).
    cleanup_environment()

    logger.info("=== Starting Madonna Military History FazzTV broadcast ===")

    # Load episode data.
    data = load_madonna_data()
    episodes = data.get('episodes')
    #= [ep for ep in data.get('episodes', []) if ep.get('guid') in args.guids]
    if not episodes:
        logger.error("No matching episodes found for provided GUIDs")
        sys.exit(1)


    # Create broadcaster.
    rtmp_url = (f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
                if STREAM_KEY else "rtmp://127.0.0.1:1935/live/test")
    broadcaster = RTMPBroadcaster(rtmp_url=rtmp_url)

    media_items = []
    for episode in episodes:
        # Ensure GUID exists.
        guid = episode.get('guid')
        if not guid:
            guid = str(uuid.uuid4())
            episode['guid'] = guid
            logger.info(f"Generated new GUID {guid} for episode '{episode['title']}'")
        temp_dir = os.path.join(tempfile.gettempdir(), "fazztv")
        # Build temporary file paths.
        audio_path = os.path.join(temp_dir, f"madonna_audio_{guid}.aac")
        video_path = os.path.join(temp_dir, f"madonna_video_{guid}.mp4")

        # Process audio: if missing, attempt download and cache by GUID.
        if not episode.get("audio_file", "").strip():
            logger.debug(f"Attempting to download/retrieve audio for {episode['title']} (GUID: {guid})")
            if not download_audio_only(episode['music_url'], audio_path, guid):
                logger.error(f"Failed to download audio for {episode['title']}")
                if episode.get('alternative_music_url'):
                    logger.info(f"Trying alternative music URL for {episode['title']}")
                    if not download_audio_only(episode['alternative_music_url'], audio_path, guid):
                        logger.error(f"Failed to download audio from alternative URL for {episode['title']}")
                        continue
                else:
                    continue
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                logger.error(f"Audio file is missing or empty: {audio_path}")
                continue
            logger.debug(f"Successfully obtained audio at {audio_path}")
            episode["audio_file"] = audio_path

        # Process video: if missing, try to download using 'video_url' (if provided),
        # else use default video file.
        if not episode.get("video_file", "").strip():
            if episode.get("video_url", "").strip():
                logger.debug(f"Attempting to download/retrieve video for {episode['title']} (GUID: {guid})")
                if not download_video_only(episode['video_url'], video_path, guid):
                    logger.error(f"Failed to download video for {episode['title']}")
                    if os.path.exists(DEFAULT_VIDEO):
                        episode["video_file"] = DEFAULT_VIDEO
                    else:
                        continue
                else:
                    if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                        logger.error(f"Video file is missing or empty: {video_path}")
                        continue
                    logger.debug(f"Successfully obtained video at {video_path}")
                    episode["video_file"] = video_path
            elif os.path.exists(DEFAULT_VIDEO):
                episode["video_file"] = DEFAULT_VIDEO
            else:
                # Leave as empty so that create_media_item_from_episode uses a dummy.
                episode["video_file"] = ""

        media_item = create_media_item_from_episode(episode)
        if media_item:
            media_items.append(media_item)

    logger.info(f"Created {len(media_items)} media items")

    # Broadcast media items.
    results = []
    for item in media_items:
        success = broadcaster.broadcast_item(item)
        results.append((item, success))
        #if os.path.exists(item.serialized):
        #   os.remove(item.serialized)

    logger.info(f"Broadcast {sum(1 for _, success in results if success)} media items successfully")
    logger.info("=== Finished Madonna Military History FazzTV broadcast ===")


if __name__ == "__main__":
    main()
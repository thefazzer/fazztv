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
    
    # Create a unique temporary directory for this download
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use a simple filename without extension in the temp directory
        temp_base = os.path.join(temp_dir, "audio_download")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": temp_base + ".%(ext)s",  # Add extension placeholder
            "max_duration": 180,
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
            
            # Find the downloaded file in the temp directory
            downloaded_files = os.listdir(temp_dir)
            logger.debug(f"Files in temp directory: {downloaded_files}")
            
            if not downloaded_files:
                logger.error("No files found in temporary directory after download")
                return False
            
            # Look specifically for the audio file with .aac extension
            audio_file = None
            for file in downloaded_files:
                if file.startswith("audio_download") and file.endswith(".aac"):
                    audio_file = os.path.join(temp_dir, file)
                    break
            
            # If no .aac file found, try to find any non-empty file
            if not audio_file:
                for file in downloaded_files:
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                        audio_file = file_path
                        break
            
            if not audio_file:
                logger.error("No valid audio file found in temporary directory")
                return False
                
            logger.debug(f"Found downloaded audio file: {audio_file}")
            
            # Copy the file to the desired output location
            import shutil
            shutil.copy2(audio_file, output_file)
            logger.debug(f"Copied audio file to {output_file}")
            
            # Verify the output file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return True
            else:
                logger.error(f"Output file {output_file} is missing or empty after copy")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

def download_video_only(url, output_file):
    """Download only the video from a YouTube video."""
    logger.debug(f"Downloading video from {url} to {output_file}")
    import yt_dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]",
         "max_duration": 180,
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
    fztv_logo_exists = os.path.exists("fztv-logo.png")
    madmil_image_exists = os.path.exists("madmil-disk2.png")
    
    # Prepare input arguments for FFmpeg
    input_args = [
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
    ]
    
    # Add logo and image inputs if they exist
    if fztv_logo_exists:
        input_args.extend(["-i", "fztv-logo.png"])
    
    if madmil_image_exists:
        input_args.extend(["-i", "madmil-disk2.png"])  # Static image to be rotated
    
    # Escape single quotes in text
    safe_title = documentary_title.replace("'", "\\'")
    
    # Build the filter complex string in parts
    filters = []
    
    # Create black column on the left
    filters.append("color=c=black:s=160x360[black_col]")  # 4cm wide black column assuming 40px/cm
    
    # Scale and prepare main video
    filters.append("[0:v]scale=1120:360,setsar=1[v0]")
    
    # Combine black column and video side by side
    filters.append("[black_col][v0]hstack[out_v]")
    
    # Add title overlay
    filters.append(
        "[out_v]drawtext=text='" + safe_title + "':"
        "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
        "fontsize=24:fontcolor=cyan:bordercolor=green:borderw=2:"
        "x=(w-text_w)/2:y=15:enable=1[titled]"
    )
    
    # Add song info overlay
    filters.append(
        "[titled]drawtext=textfile=" + song_path + ":"
        "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
        "fontsize=10:fontcolor=black:bordercolor=green:borderw=1:"
        "x=(w-text_w)/2:y=35:enable=1[titledbylined]"
    )
    
    # Add marquee
    filters.append("[2:v]scale=1280:100[marq]")
    filters.append("[titledbylined][marq]overlay=0:260[temp]")
    
    # Add FZTV logo if it exists, aligned within black column
    next_input = 3  # Start with input index 3
    last_output = "temp"
    
    if fztv_logo_exists:
        filters.append(f"[{next_input}:v]scale=100:-1[logosize]")
        filters.append(f"[{last_output}][logosize]overlay=10:10[logo1]")
        last_output = "logo1"
        next_input += 1
    
    # Add MADMIL image if it exists, positioned below the FZTV logo, inside the black column, with rotation
    if madmil_image_exists:
        filters.append(f"[{next_input}:v]scale=100:-1,rotate=2*PI*t/10:ow=rotw(iw):oh=roth(ih):c=black[madmilimg]")  # Rotate slowly over 10 seconds
        filters.append(f"[{last_output}][madmilimg]overlay=10:120[outv]")  # Positioning in black column
    else:
        filters.append(f"[{last_output}]copy[outv]")
    
    # Join all filter parts with semicolons
    filter_complex = ";".join(filters)
    
    # Build FFmpeg command
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + input_args + [  # Add loglevel error to reduce output
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-t", str(ELAPSED_TUNE_SECONDS),  # Limit output to configured duration
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
    
    try:
        # Extract song name from title
        song_match = re.match(r"^(.*?)\s*\(", episode['title'])
        song_name = song_match.group(1) if song_match else "Unknown Song"
        
        # Create temporary files with proper extensions
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"madonna_audio_{int(time.time())}.aac")
        video_path = os.path.join(temp_dir, f"madonna_video_{int(time.time())}.mp4")
        output_path = os.path.join(temp_dir, f"madonna_output_{int(time.time())}.mp4")
        
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
        war_url = episode.get('war_url', "https://www.youtube.com/watch?v=8a8fqGpHgsk")
        logger.debug(f"Attempting to download video from {war_url} to {video_path}")
        if not download_video_only(war_url, video_path):
            logger.error(f"Failed to download video for {episode.get('war_title', 'Unknown War')}")
            return None
            
        # Verify the video file exists and has content
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            logger.error(f"Video file is missing or empty: {video_path}")
            return None
            
        logger.debug(f"Successfully downloaded video to {video_path}")
        
        # Combine audio and video
        logger.debug(f"Combining audio ({audio_path}) and video ({video_path}) to {output_path}")
        war_title = episode.get('war_title', 'Unknown War Documentary')
        if not combine_audio_video(audio_path, video_path, output_path, episode['title'], episode['commentary'], war_title):
            logger.error(f"Failed to combine audio and video for {episode['title']}")
            return None
        
        # Create MediaItem
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
    except Exception as e:
        logger.error(f"Error in create_media_item: {e}")
        # Log the traceback for more detailed debugging
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

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
from datetime import date, datetime
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
import uuid
import shutil

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
CACHE_DIR = os.path.join("/tmp", "fazztv")
os.makedirs(CACHE_DIR, exist_ok=True)

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
        cached_file = os.path.join(CACHE_DIR, f"{guid}_audio.aac")
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
                cached_file = os.path.join(CACHE_DIR, f"{guid}_audio.aac")
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
                        cached_file = os.path.join(CACHE_DIR, f"{guid}_audio.aac")
                        logger.debug(f"Caching audio file to {cached_file}")
                        shutil.copy(output_file, cached_file)
                        
                    return True
            
            logger.error(f"No valid audio file found for {base_output} with any expected extension")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return False

def calculate_days_old(song_info: str) -> int:
    today = date.today()
    madonna_year = 1983  # Madonna's first album release year
    
    # Extract month and day from song_info
    date_match = re.search(r'- ([A-Za-z]+) (\d{1,2}) \d{4}$', song_info)
    if date_match:
        month_str = date_match.group(1)
        day = int(date_match.group(2))
        
        # Convert month name to number
        month = datetime.strptime(month_str, '%B').month
        
        # Create reference date using Madonna's year but war event's month/day
        reference_date = date(madonna_year, month, day)
        days_old = (today - reference_date).days
        return days_old
    return 0

def download_video_only(url, output_file, guid=None):
    """Download only the video from a YouTube video."""
    # Check if cached file exists
    if guid:
        cached_file = os.path.join(CACHE_DIR, f"{guid}_video.mp4")
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
            cached_file = os.path.join(CACHE_DIR, f"{guid}_video.mp4")
            logger.debug(f"Caching video file to {cached_file}")
            shutil.copy(output_file, cached_file)
            
        return True
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False

def combine_audio_video(
    audio_file,
    video_file,
    output_file,
    song_info,
    war_info,
    release_date,
    disable_eq=False,
    war_url=None  # Add war_url parameter
):
    """
    Combine:
      1) video_file + audio_file
      2) scrolling marquee at bottom
      3) a graphic equalizer “footer” from the snippet (if disable_eq=False)
      4) The title replaced by:
         “This song is X days old today - so ancient Madonnas release date was closer in history to the {war_title_part} !”
         where war_title_part is everything before the first colon in war_info.

    Parameters:
      audio_file (str): Path to input audio
      video_file (str): Path to input video
      output_file (str): Path to output combined file
      song_info (str): Text for the byline
      war_info (str): Text for marquee
      release_date (str): Possibly "YYYY-MM-DD", else ignored
      disable_eq (bool): If True, skip the graphic EQ entirely (default True).
      war_url (str): URL of the war documentary (for intro audio)
    """
    import datetime
    import subprocess
    import tempfile
    import os
    import logging
    import re

    logger = logging.getLogger(__name__)

    today = datetime.date.today()
    from datetime import datetime
    days_old = 0

    def sanitize_for_drawtext(s: str) -> str:
        if not s:
            return ""
        s = s.replace('\n', ' ').replace('\r', ' ')
        s = s.replace(';', ' ').replace("'", "\\'").replace(':', ' ').replace(',', ' ')
        s = re.sub(r'[\\](?![\'[\]=,@])', '', s)
        return s

    
    war_info_sanitized = sanitize_for_drawtext(war_info)

    days_old = release_date

    war_title_part = war_info.split(":", 1)[0].strip()
    
    new_title_text = (
        f"This song is {days_old} days old today and so ancient  "
        f"Madonnas release date was closer in history to {war_info} !"
    )
    safe_title = new_title_text.replace("'", "\\'")

    logger.debug(f"Combining {audio_file} + {video_file} => {output_file}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as song_file:
        song_path = song_file.name
        song_file.write(song_info)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as war_file:
        war_path = war_file.name
        war_file.write(war_info_sanitized)

    fztv_logo_exists = os.path.exists("fztv-logo.png")
    madmil_video_exists = os.path.exists("madonna-rotator.mp4")

    marquee_text_expr = (
        "color=c=black:s=2080x50,"
        "drawtext='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
        f"textfile={war_path}:"
        "fontsize=24:fontcolor=white:bordercolor=black:borderw=3:"
        "x=w - mod(40*t\\, w+text_w):"
        "y=h-th-10'"
    )

    eq_bg_expr = "color=black:s=2080x200"

    input_args = [
        "-i", video_file,
        "-i", audio_file,
        "-f", "lavfi", "-i", marquee_text_expr,
        "-f", "lavfi", "-i", eq_bg_expr
    ]
    if fztv_logo_exists:
        input_args += ["-i", "fztv-logo.png"]
    if madmil_video_exists:
        input_args += ["-stream_loop", "-1", "-i", "madonna-rotator.mp4"]

    filter_main = [
        "color=c=black:s=200x608[black_col]",
        "[0:v]scale=2080:1170:force_original_aspect_ratio=decrease,setsar=1[v0]",
        "[black_col][v0]hstack[out_v]",
        # Replace the current drawtext with two separate ones - war title and safe_title
        f"[out_v]drawtext=text='{war_info}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=50:fontcolor=red:bordercolor=black:borderw=4:x=(w-text_w)/2:y=30[war_titled]",
        f"[war_titled]drawtext=text='{song_info}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=40:fontcolor=yellow:bordercolor=black:borderw=4:x=(w-text_w)/2:y=90[titled]",
        f"[titled]drawtext=text={new_title_text}:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:fontsize=26:fontcolor=white:bordercolor=black:borderw=3:x=(w-text_w)/2:y=160[titledbylined]",
        "[2:v]scale=2080:50[marq]",
        "[titledbylined][marq]overlay=0:main_h-overlay_h-10[outv]"
    ]

    next_input = 4
    last_output = "outv"
    if fztv_logo_exists:
        filter_main.append(f"[{next_input}:v]scale=120:120[logosize]")
        filter_main.append(f"[{last_output}][logosize]overlay=20:20[logo1]")
        last_output = "logo1"
        next_input += 1
    if madmil_video_exists:
        filter_main.append(f"[{next_input}:v]scale=150:150,setpts=PTS-STARTPTS[madmilvid]")
        filter_main.append(f"[{last_output}][madmilvid]overlay=10:h-160[mainOut]")
    else:
        filter_main.append(f"[{last_output}]copy[mainOut]")

    debug_info = {
        'stage': 'initialization',
        'dimensions': {},
        'filter_graph': {},
        'stream_info': {},
        'error_context': {}
    }

    def log_debug_state(stage, **kwargs):
        """Log detailed state for LLM analysis"""
        debug_info['stage'] = stage
        debug_info.update(kwargs)
        logger.debug(f"DEBUG_STATE_{stage}: {json.dumps(debug_info, indent=2)}")

    def validate_filter_node(node_name, width, height, expected_width, expected_height):
        """Validate filter node dimensions"""
        valid = width == expected_width and height == expected_height
        debug_info['filter_graph'][node_name] = {
            'actual': f"{width}x{height}",
            'expected': f"{expected_width}x{expected_height}",
            'valid': valid
        }
        if not valid:
            logger.error(f"DIMENSION_MISMATCH_{node_name}: Expected {expected_width}x{expected_height}, got {width}x{height}")
        return valid

    # Constants with validation context
    TARGET_WIDTH = 2080
    TARGET_HEIGHT = 1170
    MARQUEE_HEIGHT = 50
    EQ_HEIGHT = 200

    # Probe and validate all input streams
    for idx, file in enumerate([video_file, audio_file]):
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=width,height,codec_type,pix_fmt,r_frame_rate",
                "-of", "json", file
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            stream_info = json.loads(result.stdout)
            debug_info['stream_info'][f'input_{idx}'] = stream_info
            log_debug_state('input_probe', file=file, stream_info=stream_info)
        except Exception as e:
            logger.error(f"PROBE_FAILURE: {e}")
            debug_info['error_context']['probe_failure'] = str(e)
            return False

    # Pre-validate filter graph components
    filter_components = []
    try:
        # Initial scale
        scale_filter = f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,setsar=1[scaled]"
        filter_components.append(('scale', scale_filter))
        
        # Marquee
        marquee_filter = f"color=black:s={TARGET_WIDTH}x{MARQUEE_HEIGHT}[marq]"
        filter_components.append(('marquee', marquee_filter))
        
        # EQ background
        if not disable_eq:
            eq_filter = f"color=black:s={TARGET_WIDTH}x{EQ_HEIGHT}[eq_bg]"
            filter_components.append(('eq', eq_filter))

        # Validate each component
        for name, filter_str in filter_components:
            validate_cmd = ["ffmpeg", "-v", "error", "-filter_complex_script", "-"]
            result = subprocess.run(validate_cmd, input=filter_str.encode(), capture_output=True)
            debug_info['filter_graph'][f'validate_{name}'] = {
                'filter': filter_str,
                'valid': result.returncode == 0,
                'error': result.stderr.decode() if result.returncode != 0 else None
            }
            log_debug_state('filter_validation', component=name)

    except Exception as e:
        logger.error(f"FILTER_VALIDATION_FAILURE: {e}")
        debug_info['error_context']['filter_validation'] = str(e)
        return False

    # Build and validate complete filter graph
    try:
        filter_complex = ";".join([f[1] for f in filter_components])
        debug_info['filter_graph']['complete'] = filter_complex
        log_debug_state('filter_graph_complete')
        
        # Validate final dimensions at each stage
        for stage in ['main', 'marquee', 'eq']:
            expected_width = TARGET_WIDTH
            expected_height = TARGET_HEIGHT + MARQUEE_HEIGHT + (EQ_HEIGHT if not disable_eq else 0)
            if not validate_filter_node(stage, expected_width, expected_height, TARGET_WIDTH, expected_height):
                return False

    except Exception as e:
        logger.error(f"FILTER_GRAPH_ASSEMBLY_FAILURE: {e}")
        debug_info['error_context']['filter_assembly'] = str(e)
        return False

    cmd = [
        "ffmpeg", "-y",
        "-progress", "pipe:1",
        "-v", "verbose",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[outfinal]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        output_file
    ]

    logger.debug("FFmpeg cmd: " + " ".join(cmd))
    logger.info("FFmpeg command for manual execution:\n" + " \\\n".join(cmd))

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Monitor progress with detailed state tracking
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                debug_info['progress'] = output.strip()
                log_debug_state('ffmpeg_progress')

        # Capture and analyze FFmpeg output
        stdout, stderr = process.communicate()
        debug_info['ffmpeg_output'] = {
            'stdout': stdout,
            'stderr': stderr,
            'return_code': process.returncode
        }
        log_debug_state('ffmpeg_complete')

        # Validate output file
        if process.returncode == 0:
            output_probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_type",
                 "-of", "json", output_file],
                capture_output=True, text=True
            )
            debug_info['output_validation'] = json.loads(output_probe.stdout)
            log_debug_state('output_validation')

        return process.returncode == 0

    except Exception as e:
        logger.error(f"FFMPEG_EXECUTION_FAILURE: {e}")
        debug_info['error_context']['ffmpeg_execution'] = str(e)
        return False

    finally:
        # Dump complete debug state for LLM analysis
        with open(f"debug_state_{int(time.time())}.json", 'w') as f:
            json.dump(debug_info, f, indent=2)

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
                age_days = calculate_days_old(episode['title'])
                age_text = (
                    f"This song is {age_days} days old today\\n"
                    f"- so ancient Madonna's release date was closer in history\\n"
                    f"to the {war_topic}!"
                ).replace("'", r"\\'")

                filter_expr = (
                    f"[0:v]drawtext=text='{title_text}':fontsize=50:fontcolor=red:bordercolor=black:borderw=4:"
                    f"x=(w-text_w)/2:y=30[v1];"
                    f"[v1]drawtext=text='{war_text}':fontsize=40:fontcolor=yellow:bordercolor=black:borderw=4:"
                    f"x=(w-text_w)/2:y=90[v2];"
                    f"[v2]drawtext=text='{age_text}':"
                    "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf:"
                    "fontsize=32:fontcolor=white:bordercolor=black:borderw=3:x=(w-text_w)/2:y=160:line_spacing=10[v3];"
                    "[v3]format=yuv420p[vout]"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=2080x1170",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex", filter_expr,
                    "-map", "[vout]", "-map", "1:a",
                    "-t", "10",
                    "output.mp4"
                ]

                subprocess.run(cmd, check=True)

            except Exception as e:
                print("Error:", e)

                subprocess.run(cmd, check=True)
                
                # Create MediaItem
                media_item = MediaItem(
                    artist="Madonna",
                    song=song_name,
                    url="",  # Empty URL since we're not using real media
                    taxprompt=episode['commentary'],
                    length_percent=100,
                    duration=ELAPSED_TUNE_SECONDS
                )
                media_item.serialized = output_path
                return media_item
            
    except Exception as e:
        logger.error(f"Error in create_media_item: {e}")
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
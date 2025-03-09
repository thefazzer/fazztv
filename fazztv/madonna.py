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
ELAPSED_TUNE_SECONDS = 10  # Default duration for media clips in seconds

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
         "max_duration": ELAPSED_TUNE_SECONDS,
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
def combine_audio_video(
    audio_file,
    video_file,
    output_file,
    song_info,
    war_info,
    release_date
):
    """
    Combine:
      1) video_file + audio_file
      2) scrolling marquee at bottom
      3) a graphic equalizer “footer” from the snippet
      4) The title replaced by:
         “This song is X days old today - so ancient Madonna's release date was closer in history to the  {war_title_part} !”
         where war_title_part is everything before the first colon in war_info.
    """

    import datetime
    import subprocess
    import tempfile
    import os
    import logging
    import re

    logger = logging.getLogger(__name__)

    # Compute days_old if release_date matches YYYY-MM-DD
    today = datetime.date.today()
    from datetime import datetime

    days_old = 0
    if re.match(r'^\d{4}-\d{2}-\d{2}$', release_date):
        release_date_val = datetime.strptime(release_date, '%Y-%m-%d').date()
        days_old = (today - release_date_val).days

    war_info_safe = war_info.replace('\n', ' ').replace(';', ',')
    war_file.write(war_info_safe)

    # Extract everything before the first colon in war_info
    war_title_part = war_info.split(":", 1)[0].strip()

    # Build the new title text
    new_title_text = (
        f"This song is {days_old} days old today - so ancient  "
        f"Madonna's release date was closer in history to the  {war_title_part} !"
    )
    # Escape single quotes
    safe_title = new_title_text.replace("'", "\\'")

    logger.debug(f"Combining {audio_file} + {video_file} => {output_file}")

    # Temporary text files for byline (song_info) and marquee (war_info)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as song_file:
        song_path = song_file.name
        song_file.write(song_info)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as war_file:
        war_path = war_file.name
        war_file.write(war_info)

    fztv_logo_exists = os.path.exists("fztv-logo.png")
    madmil_video_exists = os.path.exists("madonna-rotator.mp4")

    # Marquee input (#2): wrap drawtext in single quotes to avoid FFmpeg parse errors with colons
    # Also note we escape the comma in mod(40*t\, w+text_w).
    marquee_text_expr = (
        "color=c=black:s=1280x50,"
        "drawtext='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
        f"textfile={war_path}:"
        "fontsize=24:fontcolor=white:bordercolor=black:borderw=3:"
        "x=w - mod(40*t\\, w+text_w):"
        "y=h-th-10'"
    )

    # EQ background input (#3)
    eq_bg_expr = "color=black:s=400x400"

    # Input arguments
    #   [0]: video_file
    #   [1]: audio_file
    #   [2]: marquee
    #   [3]: eq background
    #   [4]: fztv logo (optional)
    #   [5]: madonna rotator (optional)
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

    # ---- MAIN VIDEO + MARQUEE CHAIN => [mainOut]
    filter_main = [
        # Black column
        "color=c=black:s=200x720[black_col]",
        # Scale main video
        "[0:v]scale=1080:720:force_original_aspect_ratio=decrease,setsar=1[v0]",
        # hstack side by side
        "[black_col][v0]hstack[out_v]",
        # Title
        (
            f"[out_v]drawtext=text='{safe_title}':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=50:fontcolor=yellow:bordercolor=black:borderw=4:"
            "x=(w-text_w)/2:y=90[titled]"
        ),
        # Byline below title
        (
            f"[titled]drawtext=textfile={song_path}:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "fontsize=26:fontcolor=white:bordercolor=black:borderw=3:"
            "x=(w-text_w)/2:y=160[titledbylined]"
        ),
        # Scale marquee (#2)
        "[2:v]scale=1280:50[marq]",
        # Overlay marquee at bottom
        "[titledbylined][marq]overlay=0:main_h-overlay_h-10[outv]"
    ]

    next_input = 4
    last_output = "outv"

    # Logo
    if fztv_logo_exists:
        filter_main.append(f"[{next_input}:v]scale=120:120[logosize]")
        filter_main.append(f"[{last_output}][logosize]overlay=20:20[logo1]")
        last_output = "logo1"
        next_input += 1

    # Madonna rotator
    if madmil_video_exists:
        filter_main.append(f"[{next_input}:v]scale=150:150,setpts=PTS-STARTPTS[madmilvid]")
        filter_main.append(f"[{last_output}][madmilvid]overlay=10:h-160[mainOut]")
    else:
        filter_main.append(f"[{last_output}]copy[mainOut]")

    # ---- EQ CHAIN => [eqOut]
    filter_eq = [
        # Low freq
        "[1:a]bandpass=frequency=40:width=20:width_type=h[s0];"
        "[s0]showvolume=b=0:c=0xFFFFFFFF:ds=log:f=0:h=100:m=p:o=v:p=1:rate=15:s=0:t=0:v=0:w=200[s1];"
        "[s1]crop=h=ih/2:w=25:x=0:y=0[s2];"
        "[s2]scale=h=200:w=-1[s3];"
        "[s3]smartblur[s4];"
        "[s4]minterpolate=fps=30:me_mode=bidir:mi_mode=mci[s5];"
        "[s5]smartblur[s6];"
        "[s6]split=2[s7][s8];"
        "[s7]vflip[s9];"
        "[s8][s9]vstack[s10];"
        "[s10]format=rgba[s11];"
        "[s11]pad=color=black@0:height=0:width=100:x=25:y=0[s12]",

        # Mid freq
        "[1:a]bandpass=frequency=155:width=95:width_type=h[s13];"
        "[s13]showvolume=b=0:c=0xFFFFFFFF:ds=log:f=0:h=100:m=p:o=v:p=1:rate=15:s=0:t=0:v=0:w=200[s14];"
        "[s14]crop=h=ih/2:w=25:x=0:y=0[s15];"
        "[s15]scale=h=200:w=-1[s16];"
        "[s16]smartblur[s17];"
        "[s17]minterpolate=fps=30:me_mode=bidir:mi_mode=mci[s18];"
        "[s18]smartblur[s19];"
        "[s19]split=2[s20][s21];"
        "[s20]vflip[s22];"
        "[s21][s22]vstack[s23];"
        "[s23]format=rgba[s24];"
        "[s24]pad=color=black@0:height=0:width=100:x=25:y=0[s25]",

        # Upper-mid freq
        "[1:a]bandpass=frequency=375:width=125:width_type=h[s26];"
        "[s26]showvolume=b=0:c=0xFFFFFFFF:ds=log:f=0:h=100:m=p:o=v:p=1:rate=15:s=0:t=0:v=0:w=200[s27];"
        "[s27]crop=h=ih/2:w=25:x=0:y=0[s28];"
        "[s28]scale=h=200:w=-1[s29];"
        "[s29]smartblur[s30];"
        "[s30]minterpolate=fps=30:me_mode=bidir:mi_mode=mci[s31];"
        "[s31]smartblur[s32];"
        "[s32]split=2[s33][s34];"
        "[s33]vflip[s35];"
        "[s34][s35]vstack[s36];"
        "[s36]format=rgba[s37];"
        "[s37]pad=color=black@0:height=0:width=100:x=25:y=0[s38]",

        # High freq
        "[1:a]bandpass=frequency=1250:width=750:width_type=h[s39];"
        "[s39]showvolume=b=0:c=0xFFFFFFFF:ds=log:f=0:h=100:m=p:o=v:p=1:rate=15:s=0:t=0:v=0:w=200[s40];"
        "[s40]crop=h=ih/2:w=25:x=0:y=0[s41];"
        "[s41]scale=h=200:w=-1[s42];"
        "[s42]smartblur[s43];"
        "[s43]minterpolate=fps=30:me_mode=bidir:mi_mode=mci[s44];"
        "[s44]smartblur[s45];"
        "[s45]split=2[s46][s47];"
        "[s46]vflip[s48];"
        "[s47][s48]vstack[s49];"
        "[s49]format=rgba[s50];"
        "[s50]pad=color=black@0:height=0:width=100:x=25:y=0[s51]",

        # Combine bars horizontally
        "[s12][s25][s38][s51]hstack=inputs=4[s52]",
        # Overlay bars on [3:v] => eqOut
        "[3:v][s52]overlay[eqOut]"
    ]

    # Finally vstack mainOut + eqOut => outfinal
    filter_combine = [
        "[mainOut][eqOut]vstack=inputs=2[outfinal]"
    ]

    # Combine filter strings
    filter_complex = (
        ";".join(filter_main)
        + ";"
        + ";".join(filter_eq)
        + ";"
        + ";".join(filter_combine)
    )

    cmd = ["ffmpeg", "-y"] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[outfinal]",  # final video
        "-map", "1:a",         # main audio
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-r", "30", "-vsync", "2",
        "-movflags", "+faststart",
        output_file
    ]

    logger.debug("FFmpeg cmd: " + " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            logger.error("FFmpeg error: " + result.stderr.decode("utf-8", "ignore"))
            return False
        return True
    except Exception as e:
        logger.error(f"FFmpeg exception: {e}")
        return False
    finally:
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
        
        # Check if audio file already exists with a consistent naming pattern
        audio_filename = f"madonna_audio_{song_name.replace(' ', '_')}.aac"
        existing_audio_path = os.path.join(temp_dir, audio_filename)
        
        if os.path.exists(existing_audio_path) and os.path.getsize(existing_audio_path) > 0:
            logger.info(f"Using existing audio file: {existing_audio_path}")
            audio_path = existing_audio_path
        else:
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
            
        logger.debug(f"Successfully obtained audio at {audio_path}")
        
        # Check if video file already exists with a consistent naming pattern
        war_title = episode.get('war_title', 'Unknown War Documentary')
        video_filename = f"madonna_video_{war_title.replace(' ', '_')}.mp4"
        existing_video_path = os.path.join(temp_dir, video_filename)
        
        if os.path.exists(existing_video_path) and os.path.getsize(existing_video_path) > 0:
            logger.info(f"Using existing video file: {existing_video_path}")
            video_path = existing_video_path
        else:
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
            
        logger.debug(f"Successfully obtained video at {video_path}")
        
        # Combine audio and video
        logger.debug(f"Combining audio ({audio_path}) and video ({video_path}) to {output_path}")
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
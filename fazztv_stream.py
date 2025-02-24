import yt_dlp
import openai
import subprocess
import time
import random
import os
import textwrap
import json
from loguru import logger
from config import *

class StreamState:
    def __init__(self):
        self.current_singer = None
        self.current_song_title = None
        self.current_tax_info = None
        self.next_singer = None
        self.next_song_title = None
        self.next_tax_info = None
        
    def log_state(self):
        logger.info("=== Stream State ===")
        logger.info("NOW PLAYING:")
        logger.info(f"  Artist: {self.current_singer}")
        logger.info(f"  Song: {self.current_song_title}")
        logger.info(f"  Marquee: {self.current_tax_info[:100]}...")
        logger.info("NEXT UP:")
        logger.info(f"  Artist: {self.next_singer}")
        logger.info(f"  Song: {self.next_song_title}")
        logger.info(f"  Marquee: {self.next_tax_info[:100]}...")
        logger.info("================")

    def update_current(self, singer, song_title, tax_info):
        self.current_singer = singer
        self.current_song_title = song_title
        self.current_tax_info = tax_info
        
    def update_next(self, singer, song_title, tax_info):
        self.next_singer = singer
        self.next_song_title = song_title
        self.next_tax_info = tax_info
        
    def promote_next_to_current(self):
        self.current_singer = self.next_singer
        self.current_song_title = self.next_song_title
        self.current_tax_info = self.next_tax_info
        self.next_singer = None
        self.next_song_title = None
        self.next_tax_info = None

def debug_log_subprocess_result(res, stage=""):
    logger.debug(f"{stage} => Return code: {res.returncode}")
    if res.stdout:
        logger.debug(f"{stage} => STDOUT:\n{res.stdout.decode('utf-8','ignore')}")
    if res.stderr:
        logger.debug(f"{stage} => STDERR:\n{res.stderr.decode('utf-8','ignore')}")

def safe_get_tax_info(singer):
    logger.debug(f"Requesting tax info for {singer} via OpenAI...")
    try:
        facts = get_tax_info(singer)
        logger.debug(f"Successfully got tax info for {singer}")
        return facts
    except Exception as e:
        logger.error(f"OpenAI error for {singer}: {e}")
        return "Tax info unavailable (OpenAI quota exceeded)."

def get_tax_info(singer):
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": (
                f"Provide a concise summary of {singer}'s tax problems, including key dates, "
                "fines, amounts, or relevant penalties."
            )
        }]
    )
    facts = resp["choices"][0]["message"]["content"]
    logger.info(f"Tax info for {singer}: {facts}")
    return facts

def get_video_duration(filename):
    logger.debug(f"Probing duration for {filename}")
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", filename]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
        logger.debug(f"Duration of {filename}: {duration:.2f}s")
        return duration
    except:
        logger.error(f"Could not read duration for {filename}")
        return 0.0

def get_random_song_url(singer):
    logger.debug(f"Searching random official music video for {singer}...")
    query = f"{singer} official music video"
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
                logger.error(f"No videos for {singer}")
                return None, None
            pick = random.choice(vids)
            logger.info(f"Selected for {singer}: {pick['title']} ({pick['webpage_url']})")
            return pick["webpage_url"], pick["title"]
    except Exception as e:
        logger.error(f"Error searching {singer}: {e}")
        return None, None

def download_video(url, output_filename):
    logger.debug(f"Downloading {url} => {output_filename}")
    ydl_opts = {
        "format": "best",
        "outtmpl": output_filename,
        "quiet": True,
        "overwrites": True,
        "continuedl": False
    }
    try:
        if os.path.exists(output_filename):
            os.remove(output_filename)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        exists = os.path.exists(output_filename)
        logger.debug(f"Downloaded => {output_filename}? {exists}")
        return exists
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False

def ephemeral_merge_rtmp(prev_file, marquee_text, next_file):
    marquee_text = marquee_text.replace("\n", " ").replace("\r", " ")
    logger.debug(f"Marquee text => {marquee_text}")

    with open("marquee.txt", "w", encoding="utf-8") as f:
        f.write(marquee_text)

    dur1 = get_video_duration(prev_file)
    if dur1 <= 0:
        dur1 = 30
        logger.warning("prev.mp4 invalid => fallback 30s")
    fade_out_start = max(0, dur1 - FADE_LENGTH)
    logger.debug(f"Fading out prev at {fade_out_start:.2f}s")

    logo_exists = os.path.exists("fztv-logo.png")
    if logo_exists:
        logo_input = ["-i", "fztv-logo.png"]
        scale_logo  = "[3:v]scale=100:-1[logosize];"
        overlay_logo = "[temp][logosize]overlay=10:10[outv]"
    else:
        logo_input = []
        scale_logo  = ""
        overlay_logo = "[temp]copy[outv]"

    filter_str = (
        f"[0:v]scale={BASE_RES},setsar=1,fade=t=out:st={fade_out_start}:d={FADE_LENGTH}[v0];"
        f"[1:v]scale={BASE_RES},setsar=1,fade=t=in:st=0:d={FADE_LENGTH}[v1];"
        f"[0:a]afade=t=out:st={fade_out_start}:d={FADE_LENGTH}[a0];"
        f"[1:a]afade=t=in:st=0:d={FADE_LENGTH}[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[mergedv][mergeda];"
        "[2:v]scale=640:100[marq];"
        "[mergedv][marq]overlay=0:360-100[temp];"
        f"{scale_logo}"
        f"{overlay_logo}"
    )

    if STREAM_KEY:
        rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    else:
        rtmp_url = "rtmp://127.0.0.1:1935/live/test"

    cmd = [
        "ffmpeg", "-y",
        "-re", "-i", prev_file,
        "-re", "-i", next_file,
        "-re",
        "-f", "lavfi",
        "-i", (
            f"color=c=black:s=1280x100:d={MARQUEE_DURATION},"
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            "textfile=marquee.txt:"
            "fontsize=16:"
            "fontcolor=white:"
            "y=10:"
            f"x='1280 - mod(t*{SCROLL_SPEED}, 1280+text_w)':"
            "enable=1"
        )
    ] + logo_input + [
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "[mergeda]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-r", "30", "-vsync", "2",
        "-movflags", "+faststart",
        "-f", "flv",
        rtmp_url
    ]

    logger.info("Starting ephemeral merge => RTMP:")
    logger.debug(" ".join(cmd))

    # Run ffmpeg in background and return the process
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

def main():
    logger.info("=== Starting FZTV Stream ===")
    
    state = StreamState()
    
    # Initialize first song
    prev_singer = random.choice(SINGERS)
    first_url, first_title = get_random_song_url(prev_singer)
    if not first_url:
        logger.error("No URL for first singer => exit.")
        return
    if not download_video(first_url, "prev.mp4"):
        logger.error("Download first singer fail => exit.")
        return
    
    # Get first singer info
    current_info = safe_get_tax_info(prev_singer)
    state.update_current(prev_singer, first_title, current_info)
    current_process = None

    while True:
        logger.info("=== Starting iteration ===")
        state.log_state()

        # Pick next singer
        next_singer = random.choice(SINGERS)
        while next_singer == state.current_singer:
            next_singer = random.choice(SINGERS)
            
        # Get next song and info
        next_url, next_title = get_random_song_url(next_singer)
        if not next_url:
            logger.error("No URL for nextSinger => skip iteration.")
            time.sleep(5)
            continue
            
        next_info = safe_get_tax_info(next_singer)
        state.update_next(next_singer, next_title, next_info)
        
        if not download_video(next_url, "next.mp4"):
            logger.error("Download next.mp4 fail => skip iteration.")
            time.sleep(5)
            continue

        # Start new ffmpeg process
        logger.debug("Starting new ffmpeg process")
        new_process = ephemeral_merge_rtmp("prev.mp4", state.current_tax_info, "next.mp4")

        # Handle process transition
        if current_process:
            try:
                current_process.terminate()
                current_process.wait(timeout=5)
            except:
                current_process.kill()
            logger.debug("Previous ffmpeg process terminated")

        # Update state
        current_process = new_process
        os.replace("next.mp4", "prev.mp4")
        state.promote_next_to_current()
        
        logger.info("=== Finished iteration ===")
        time.sleep(30)

if __name__ == "__main__":
    main()
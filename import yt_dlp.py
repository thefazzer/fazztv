import yt_dlp
import openai
import subprocess
import time
import random
import os
import textwrap
import json
from loguru import logger

# ---------------------------------------------------------------------------
#                           CONFIGURATION
# ---------------------------------------------------------------------------
OPENAI_API_KEY = "sk-"
STREAM_KEY = None
SEARCH_LIMIT = 5
LOG_FILE = "broadcast.log"

BASE_RES = "640x360"
FADE_LENGTH = 3
MARQUEE_DURATION = 86400
SCROLL_SPEED = 40

openai.api_key = OPENAI_API_KEY

# 20 Singers
SINGERS = sorted([
    "Lauryn Hill", "Shakira", "Toni Braxton", "Willie Nelson", "Lil Wayne",
    "Fat Joe", "Ja Rule", "DMX", "R. Kelly", "Dionne Warwick",
    "Ozzy Osbourne", "Lionel Richie", "Iggy Azalea", "Flo Rida", "Akon",
    "Ron Isley", "Sean Kingston", "Nas", "MC Hammer", "Chris Tucker"
])

logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

# ---------------------------------------------------------------------------
#                       HELPER FUNCTIONS
# ---------------------------------------------------------------------------

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
    import yt_dlp
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
                return None
            pick = random.choice(vids)
            logger.info(f"Selected for {singer}: {pick['title']} ({pick['webpage_url']})")
            return pick["webpage_url"]
    except Exception as e:
        logger.error(f"Error searching {singer}: {e}")
        return None

def download_video(url, output_filename):
    logger.debug(f"Downloading {url} => {output_filename}")
    import yt_dlp
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
    """
    Single ephemeral ffmpeg:
      #0 => prev.mp4
      #1 => next.mp4
      #2 => single-line marquee
      #3 => optional fztv-logo.png
    We fade out #0 near end, fade in #1 from 0..3, show 'marquee_text' for nextSinger,
    then push => RTMP.
    """
    # Flatten multiline to single line
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

    # Check logo
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

    res = subprocess.run(cmd, capture_output=True)
    debug_log_subprocess_result(res, stage="Ephemeral ffmpeg")

    return res

def main():
    logger.info("=== Indefinite ephemeral merges with nextSinger info on marquee ===")

    # 1) Start with an initial "prev.mp4" (any random singer)
    prev_singer = random.choice(SINGERS)
    logger.debug(f"Chosen FIRST singer => {prev_singer}")
    first_url = get_random_song_url(prev_singer)
    if not first_url:
        logger.error("No URL for first singer => exit.")
        return
    if not download_video(first_url, "prev.mp4"):
        logger.error("Download first singer fail => exit.")
        return
    logger.debug("Completed download => prev.mp4")

    # 2) Now infinite loop
    while True:
        logger.info("=== Starting ephemeral iteration ===")

        # a) pick nextSinger => fetch info
        next_singer = random.choice(SINGERS)
        logger.debug(f"Chosen next singer => {next_singer}")
        next_info = safe_get_tax_info(next_singer)
        logger.info(f"Next singer snippet => {next_info[:80]}")

        # b) download nextSinger video => next.mp4
        next_url = get_random_song_url(next_singer)
        if not next_url:
            logger.error("No URL for nextSinger => skip iteration.")
            time.sleep(5)
            continue
        if not download_video(next_url, "next.mp4"):
            logger.error("Download next.mp4 fail => skip iteration.")
            time.sleep(5)
            continue

        # c) ephemeral merge => show nextSinger info
        logger.debug("Running ephemeral merge => using nextSinger info on marquee.")
        res = ephemeral_merge_rtmp("prev.mp4", next_info, "next.mp4")
        logger.debug(f"Merging return code => {res.returncode}")
        if res.returncode != 0:
            logger.error("Ephemeral merge failed => skip iteration.")
            time.sleep(5)
            continue

        # d) rename next => prev
        logger.debug("Renaming next.mp4 => prev.mp4 for next iteration")
        os.replace("next.mp4", "prev.mp4")

        logger.info("=== Finished ephemeral iteration ===")
        time.sleep(2)

if __name__ == "__main__":
    main()
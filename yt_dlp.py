# Remove/modify the top import
# import yt_dlp.py:1-280  <- This line should be removed if it exists

import yt_dlp
import openai
import subprocess
import time
import random
import os
import textwrap
import json
from loguru import logger

# ... existing code ...

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
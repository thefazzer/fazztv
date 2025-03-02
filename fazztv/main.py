import random
import time
import os
import openai
from loguru import logger
import requests

from fazztv.models import MediaItem
from fazztv.serializer import MediaSerializer
from fazztv.broadcaster import RTMPBroadcaster
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Access variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
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
    "Lauryn Hill", "Shakira", 
     "Toni Braxton", "Willie Nelson", "Lil Wayne",
    #"Fat Joe", "Ja Rule", "DMX", "R. Kelly", "Dionne Warwick",
    #"Ozzy Osbourne", "Lionel Richie", "Iggy Azalea", "Flo Rida", "Akon",
    #"Ron Isley", "Sean Kingston", "Nas", "MC Hammer", "Chris Tucker"
])

ftv_shows = [
    {"title": "Tax Evasion Nation", "byline": "A deep dive into the biggest tax scandals in music."},
    {"title": "Audit This!", "byline": "When the IRS comes knocking, these artists start rocking."},
    {"title": "Cash Under the Mattress", "byline": "Where did all the money go? Hidden assets and shady deals."},
    {"title": "Behind Bars & Behind the Music", "byline": "The true crime stories of tax-dodging musicians."},
    {"title": "IRS Unplugged", "byline": "Famous cases where the taxman turned off the money tap."},
    {"title": "Fraud Files: The Remix", "byline": "A look at artists who remixed their income statements."},
    {"title": "Return to Sender", "byline": "Tax returns gone wrong and the consequences."},
    {"title": "Deduction Destruction", "byline": "When creative accounting turns criminal."},
    {"title": "Offshore & On Tour", "byline": "Rockstars, shell companies, and secret bank accounts."},
    {"title": "Taxman’s Greatest Hits", "byline": "A countdown of the most notorious tax-dodging musicians."},
    {"title": "Hide Yo Money, Hide Yo Taxes", "byline": "When the IRS slides into your DMs with a subpoena."},
    {"title": "W2 Hell & Back", "byline": "Musicians who faked their income until the feds came knocking."},
    {"title": "Death & Taxes (But Mostly Taxes)", "byline": "Because even rockstars can’t escape the taxman."},
    {"title": "Straight Outta Cayman", "byline": "The offshore accounts that almost worked."},
    {"title": "No Refund, No Peace", "byline": "When dodging the IRS goes horribly wrong."},
    {"title": "Mo’ Money, Mo’ Problems: IRS Edition", "byline": "The richest, dumbest tax evaders in music."},
    {"title": "Audit Me If You Can", "byline": "A reality show where celebs try (and fail) to dodge taxes."},
    {"title": "Filing Single, Ready to Flee", "byline": "When tax fraudsters ghost the government."},
    {"title": "The Write-Offs", "byline": "Musicians who wrote off EVERYTHING… until they got caught."},
    {"title": "99 Problems & The IRS Is One", "byline": "Because Jay-Z warned us, but they didn’t listen."}
]

logger.add(LOG_FILE, rotation="10 MB", level="DEBUG")

# ---------------------------------------------------------------------------
#                       HELPER FUNCTIONS
# ---------------------------------------------------------------------------

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
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional
        "X-Title": "<YOUR_SITE_NAME>",  # Optional
    }
    
    data = {
        "model": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Provide a concise summary of {singer}'s tax problems, including key dates, "
                    "fines, amounts, or relevant penalties."
                )
            }
        ],
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raises an error for HTTP errors
        result = response.json()

        # Ensure the expected structure exists before accessing
        if "choices" in result and result["choices"]:
            message_content = result["choices"][0].get("message", {}).get("content", "")
            if message_content:
                logger.info(f"Tax info for {singer}: {message_content[:100]}...")  # Log first 100 chars
                return message_content
            else:
                logger.error(f"No content found in response for {singer}")
                return "Tax info unavailable"
        else:
            logger.error(f"Unexpected API response structure: {result}")
            return "Tax info unavailable"

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return "Tax info unavailable"

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
                return None, None
            pick = random.choice(vids)
            logger.info(f"Selected for {singer}: {pick['title']} ({pick['webpage_url']})")
            return pick["webpage_url"], pick["title"]
    except Exception as e:
        logger.error(f"Error searching {singer}: {e}")
        return None, None

def create_media_item(artist, length_percent=10):
    """Create a MediaItem for the given artist."""
    url, song = get_random_song_url(artist)
    if not url or not song:
        logger.error(f"Could not get URL or song title for {artist}")
        return None
    
    taxprompt = safe_get_tax_info(artist)
    
    try:
        media_item = MediaItem(
            artist=artist,
            song=song,
            url=url,
            taxprompt=taxprompt,
            length_percent=length_percent
        )
        return media_item
    except ValueError as e:
        logger.error(f"Error creating MediaItem for {artist}: {e}")
        return None

def main():
    logger.info("=== Starting structured FazzTV broadcast ===")
    
    # Create serializer and broadcaster
    serializer = MediaSerializer(
        base_res=BASE_RES,
        fade_length=FADE_LENGTH,
        marquee_duration=MARQUEE_DURATION,
        scroll_speed=SCROLL_SPEED,
        logo_path="fztv-logo.png"
    )
    
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}" if STREAM_KEY else "rtmp://127.0.0.1:1935/live/test"
    broadcaster = RTMPBroadcaster(rtmp_url=rtmp_url)
    
    # Create a collection of media items
    media_items = []
    for singer in SINGERS:
        media_item = create_media_item(singer, length_percent=random.randint(50, 100))
        if media_item:
            media_items.append(media_item)
    
    logger.info(f"Created {len(media_items)} media items")
    
    # Serialize the media items
    serialized_items = []
    for item in media_items:
        if serializer.serialize_media_item(item):
            serialized_items.append(item)
    
    logger.info(f"Serialized {len(serialized_items)} media items")
    
    # Broadcast the media items with a filter
    # Example filter: only artists with 'i' in their name
    filter_func = lambda item: 'i' in item.artist.lower()
    
    results = broadcaster.broadcast_filtered_collection(serialized_items, filter_func)
    
    logger.info(f"Broadcast {len(results)} media items")
    logger.info("=== Finished FazzTV broadcast ===")

if __name__ == "__main__":
    main()
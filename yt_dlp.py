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

def get_random_song_url(singer):
    # ... existing code ...
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
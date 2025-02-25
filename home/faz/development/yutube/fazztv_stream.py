import threading
from queue import Queue
# ... existing imports ...

class ContentPreparator(threading.Thread):
    def __init__(self, queue, state):
        super().__init__()
        self.queue = queue
        self.state = state
        self.running = True
        
    def run(self):
        while self.running:
            try:
                # Pick next singer
                next_singer = random.choice(SINGERS)
                while next_singer == self.state.current_singer:
                    next_singer = random.choice(SINGERS)
                
                # Get next song and info
                next_url, next_title = get_random_song_url(next_singer)
                if not next_url:
                    logger.error("No URL for nextSinger => retrying")
                    time.sleep(5)
                    continue
                
                next_info = safe_get_tax_info(next_singer)
                
                # Download video
                if not download_video(next_url, "next.mp4"):
                    logger.error("Download next.mp4 fail => retrying")
                    time.sleep(5)
                    continue
                
                # Package the next content
                next_content = {
                    'singer': next_singer,
                    'title': next_title,
                    'tax_info': next_info,
                    'file': "next.mp4"
                }
                
                # Update state and queue
                self.state.update_next(next_singer, next_title, next_info)
                self.queue.put(next_content)
                
                # Wait until the queue is consumed
                while self.running and not self.queue.empty():
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Content preparation error: {e}")
                time.sleep(5)
    
    def stop(self):
        self.running = False

def main():
    logger.info("=== Starting FZTV Stream ===")
    
    state = StreamState()
    content_queue = Queue(maxsize=1)
    
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
    
    # Start content preparation thread
    preparator = ContentPreparator(content_queue, state)
    preparator.start()
    
    try:
        current_process = None
        
        while True:
            logger.info("=== Starting streaming iteration ===")
            state.log_state()

            # Start streaming current content
            logger.debug("Starting ffmpeg process")
            current_process = ephemeral_merge_rtmp("prev.mp4", state.current_tax_info, "next.mp4")
            
            # Wait for next content while current is streaming
            try:
                next_content = content_queue.get(timeout=180)  # 3 minute timeout
            except Queue.Empty:
                logger.error("Timeout waiting for next content")
                if current_process:
                    current_process.terminate()
                continue
                
            # Let current video play most of its duration
            video_duration = get_video_duration("prev.mp4")
            sleep_duration = max(0, video_duration - FADE_LENGTH - 5)  # 5 second buffer
            time.sleep(sleep_duration)
            
            # Update state for next iteration
            if current_process:
                try:
                    current_process.terminate()
                    current_process.wait(timeout=5)
                except:
                    current_process.kill()
                logger.debug("Previous ffmpeg process terminated")
            
            os.replace("next.mp4", "prev.mp4")
            state.promote_next_to_current()
            
            logger.info("=== Finished streaming iteration ===")
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if current_process:
            current_process.terminate()
        preparator.stop()
        preparator.join()
        
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        if current_process:
            current_process.terminate()
        preparator.stop()
        preparator.join()

if __name__ == "__main__":
    main()
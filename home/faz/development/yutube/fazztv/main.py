# ... existing code ...

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
    
    # Serialize the media items with show information
    serialized_items = []
    for item in media_items:
        if serializer.serialize_media_item(item, ftv_shows=ftv_shows):
            serialized_items.append(item)
    
    logger.info(f"Serialized {len(serialized_items)} media items")
    
    # Broadcast the media items with a filter
    # Example filter: only artists with 'i' in their name
    filter_func = lambda item: 'i' in item.artist.lower()
    
    results = broadcaster.broadcast_filtered_collection(serialized_items, filter_func)
    
    logger.info(f"Broadcast {len(results)} media items")
    logger.info("=== Finished FazzTV broadcast ===")
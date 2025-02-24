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

    # Get tax info for first singer
    prev_info = safe_get_tax_info(prev_singer)
    current_info = prev_info  # Track current singer's info

    # 2) Now infinite loop
    while True:
        logger.info("=== Starting ephemeral iteration ===")

        # a) pick nextSinger => fetch info
        next_singer = random.choice(SINGERS)
        while next_singer == prev_singer:  # Avoid repeating the same singer
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

        # c) ephemeral merge => show current singer info
        logger.debug("Running ephemeral merge => using current singer info on marquee.")
        res = ephemeral_merge_rtmp("prev.mp4", current_info, "next.mp4")
        logger.debug(f"Merging return code => {res.returncode}")
        if res.returncode != 0:
            logger.error("Ephemeral merge failed => skip iteration.")
            time.sleep(5)
            continue

        # d) prepare for next iteration
        logger.debug("Renaming next.mp4 => prev.mp4 for next iteration")
        os.replace("next.mp4", "prev.mp4")
        prev_singer = next_singer
        current_info = next_info  # Update current info for next iteration

        logger.info("=== Finished ephemeral iteration ===")
        time.sleep(2)
# ... existing code ...

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
    # ... existing code ...
    
    # Modify marquee text expression to ensure visibility and proper scrolling
    marquee_text_expr = (
        "color=c=black:s=2080x50,"
        "drawtext='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
        f"textfile={war_path}:"
        "fontsize=24:fontcolor=white:bordercolor=black:borderw=3:"
        "x=2080-(mod(t*40\\,2080+tw)):"  # Modified scrolling formula
        "y=h-th-10:"
        "reload=1:"  # Add reload parameter
        "alpha=0.9'"  # Add some transparency
    )

    # ... existing code ...

    # Modify filter_main to ensure marquee is visible
    filter_main = [
        # ... existing code ...
        "[2:v]scale=2080:50[marq]",
        "[titledbylined][marq]overlay=0:main_h-overlay_h-200[outv]",  # Adjusted y-position
        # ... rest of existing code ...
    ]

# ... existing code ...
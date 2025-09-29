"""FFmpeg utilities for FazzTV video processing."""

import os
import subprocess
from typing import List, Dict, Tuple, Any
from loguru import logger

from fazztv.config import constants
from fazztv.config.ui_constants import (
    UI_BASE_WIDTH, UI_BASE_HEIGHT, UI_MARQUEE_HEIGHT, UI_VIDEO_SCALE,
    UI_LOGO_SCALE, UI_BULB_SCALE, UI_MARQUEE_SCALE, UI_WAR_TITLE_FONT_SIZE,
    UI_TITLE_FONT_SIZE, UI_COMMENTARY_FONT_SIZE, UI_AGE_TEXT_FONT_SIZE,
    UI_WAR_TITLE_Y, UI_TITLE_Y, UI_BULB_Y, UI_BULB_X_OFFSET,
    UI_AGE_TEXT1_Y, UI_AGE_TEXT2_Y, UI_WAR_TITLE_BORDER_WIDTH,
    UI_TITLE_BORDER_WIDTH, UI_COMMENTARY_BORDER_WIDTH, UI_AGE_TEXT_BORDER_WIDTH,
    UI_MARQUEE_SCROLL_MULTIPLIER, UI_MARQUEE_Y_OFFSET, UI_LOGO_X, UI_LOGO_Y,
    UI_OVERLAY_BOTTOM_OFFSET, UI_FFMPEG_FRAME_RATE, UI_BACKGROUND_COLOR,
    UI_NULL_VIDEO_SIZE, UI_NULL_VIDEO_DURATION, UI_NULL_VIDEO_RATE,
    UI_AUDIO_SAMPLE_RATE, UI_AUDIO_CHANNELS
)
from fazztv.utils.error_handling import log_exceptions, safe_execute


def build_ffmpeg_inputs(episode: Dict[str, Any]) -> List[str]:
    """
    Build FFmpeg input arguments for media processing.

    Args:
        episode: Episode data dictionary

    Returns:
        List of FFmpeg input arguments
    """
    video_file = episode.get("video_file", "").strip()
    audio_file = episode.get("audio_file", "").strip()
    input_args = []

    # (0) Black background
    input_args.extend(["-f", "lavfi", "-i", f"color=c={UI_BACKGROUND_COLOR}:s={UI_BASE_WIDTH}x{UI_BASE_HEIGHT}"])

    # (1) Audio: use provided file if exists; else silent audio
    if audio_file:
        input_args.extend(["-i", audio_file])
    else:
        input_args.extend(["-f", "lavfi", "-i", f"anullsrc=r={UI_AUDIO_SAMPLE_RATE}:cl={UI_AUDIO_CHANNELS}"])

    # (2) Video: use provided file if exists; else default if available; else dummy
    if video_file:
        input_args.extend(["-i", video_file])
    elif os.path.exists(constants.DEFAULT_VIDEO_FILE):
        input_args.extend(["-i", constants.DEFAULT_VIDEO_FILE])
    else:
        input_args.extend(["-f", "lavfi", "-i", f"nullsrc=s={UI_NULL_VIDEO_SIZE}:d={UI_NULL_VIDEO_DURATION}:r={UI_NULL_VIDEO_RATE}"])

    return input_args


def build_marquee_text_filter(commentary: str) -> str:
    """
    Build marquee text filter for FFmpeg.

    Args:
        commentary: Commentary text to display in marquee

    Returns:
        FFmpeg marquee filter string
    """
    return (
        f"color=c={UI_BACKGROUND_COLOR}:s={UI_BASE_WIDTH}x{UI_MARQUEE_HEIGHT},"
        f"drawtext=fontfile={constants.DEFAULT_FONT}:"
        "text='" + commentary + "':"
        f"fontsize={UI_COMMENTARY_FONT_SIZE}:fontcolor={constants.COLOR_WHITE}:bordercolor={constants.COLOR_BLACK}:borderw={UI_COMMENTARY_BORDER_WIDTH}:"
        f"x=w-mod({UI_MARQUEE_SCROLL_MULTIPLIER}*t\\,w+text_w):"
        f"y=h-th-{UI_MARQUEE_Y_OFFSET}"
    )


def build_main_video_filter(texts: Dict[str, str]) -> List[str]:
    """
    Build main video filter components.

    Args:
        texts: Dictionary containing overlay text elements

    Returns:
        List of filter components
    """
    return [
        # Combine background and main video
        f"[0:v]scale={UI_VIDEO_SCALE}[bg];[2:v]scale={UI_VIDEO_SCALE}[vmain];[bg][vmain]overlay=0:0[base]",
        # War and title text overlays
        f"[base]drawtext=text='{texts['war_text']}':fontfile={constants.DEFAULT_FONT}:"
        f"fontsize={UI_WAR_TITLE_FONT_SIZE}:fontcolor={constants.COLOR_RED}:bordercolor={constants.COLOR_BLACK}:borderw={UI_WAR_TITLE_BORDER_WIDTH}:x=(w-text_w)/2:y={UI_WAR_TITLE_Y}[war_titled]",
        f"[war_titled]drawtext=text='{texts['title_text']}':fontfile={constants.DEFAULT_FONT}:"
        f"fontsize={UI_TITLE_FONT_SIZE}:fontcolor={constants.COLOR_YELLOW}:bordercolor={constants.COLOR_BLACK}:borderw={UI_TITLE_BORDER_WIDTH}:x=(w-text_w)/2:y={UI_TITLE_Y}[titled]",
        # Example overlay: a did-you-know lightbulb
        f"movie={constants.DEFAULT_LIGHTBULB_IMAGE}[bulb]",
        f"[bulb]scale={UI_BULB_SCALE}[scaled_bulb]",
        f"[titled][scaled_bulb]overlay=(W/2)-{UI_BULB_X_OFFSET}:{UI_BULB_Y}[v2_with_bulb]",
        # Age text overlay
        f"[v2_with_bulb]drawtext=text='{texts['age_text1']}':fontfile={constants.DEFAULT_FONT}:"
        f"fontsize={UI_AGE_TEXT_FONT_SIZE}:fontcolor={constants.COLOR_WHITE}:bordercolor={constants.COLOR_BLACK}:borderw={UI_AGE_TEXT_BORDER_WIDTH}:x=(w-text_w)/2:y={UI_AGE_TEXT1_Y}[titledbylined]",
        f"[titledbylined]drawtext=text='{texts['age_text2']}':fontfile={constants.DEFAULT_FONT}:"
        f"fontsize={UI_AGE_TEXT_FONT_SIZE}:fontcolor={constants.COLOR_WHITE}:bordercolor={constants.COLOR_BLACK}:borderw={UI_AGE_TEXT_BORDER_WIDTH}:x=(w-text_w)/2:y={UI_AGE_TEXT2_Y}[titledbylined]",
        # Marquee overlay
        f"[3:v]scale={UI_MARQUEE_SCALE}[marq]",
        f"[titledbylined][marq]overlay=0:main_h-overlay_h-{UI_OVERLAY_BOTTOM_OFFSET}[with_marq]"
    ]


def build_ffmpeg_filter(texts: Dict[str, str], has_logo: bool) -> Tuple[str, str]:
    """
    Build FFmpeg filter_complex for video processing.

    Args:
        texts: Dictionary containing overlay text elements
        has_logo: Whether logo file exists

    Returns:
        Tuple of (filter_complex_string, marquee_text_filter)
    """
    # Build marquee text filter
    marquee_text = build_marquee_text_filter(texts['commentary'])

    # Build main filter components
    filter_main = build_main_video_filter(texts)

    # Add logo overlay if available
    if has_logo:
        filter_main.append(f"[4:v]scale={UI_LOGO_SCALE}[logo]")
        filter_main.append(f"[with_marq][logo]overlay={UI_LOGO_X}:{UI_LOGO_Y}[outfinal]")
    else:
        filter_main.append("[with_marq]copy[outfinal]")

    return ";".join(filter_main), marquee_text


def build_ffmpeg_command(input_args: List[str], filter_complex: str, output_file: str,
                        duration_seconds: int) -> List[str]:
    """
    Build the complete FFmpeg command for video processing.

    Args:
        input_args: FFmpeg input arguments
        filter_complex: Filter complex string
        output_file: Output file path
        duration_seconds: Duration in seconds

    Returns:
        Complete FFmpeg command as list of strings
    """
    return [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-r", UI_FFMPEG_FRAME_RATE,
        "-map", "[outfinal]",
        "-map", "1:a",
        "-c:v", constants.FFMPEG_VIDEO_CODEC_HW, "-preset", constants.FFMPEG_VIDEO_PRESET,
        "-c:a", constants.AUDIO_CODEC, "-b:a", constants.FFMPEG_AUDIO_BITRATE,
        "-t", f"{duration_seconds}",
        output_file
    ]


@log_exceptions(return_value=False)
def execute_ffmpeg_command(cmd: List[str], operation_name: str = "FFmpeg processing") -> bool:
    """
    Execute FFmpeg command with proper error handling.

    Args:
        cmd: FFmpeg command as list of strings
        operation_name: Name for logging purposes

    Returns:
        True if successful, False otherwise
    """
    result = safe_execute(
        subprocess.run,
        args=(cmd,),
        kwargs={"check": True, "timeout": constants.FFMPEG_TIMEOUT, "capture_output": True, "text": True},
        operation_name=operation_name
    )

    if result is None:
        logger.error(f"{operation_name} failed")
        return False

    return True
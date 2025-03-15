import os
import subprocess
import tempfile
import json
import random
from typing import List, Optional, Tuple
from loguru import logger
from fazztv.models import MediaItem

class MediaSerializer:
    def __init__(self, base_res: str = "640x360", fade_length: int = 3,
                 marquee_duration: int = 86400, scroll_speed: int = 40,
                 logo_path: Optional[str] = "fztv-logo.png"):
        self.base_res = base_res
        self.fade_length = fade_length
        self.marquee_duration = marquee_duration
        self.scroll_speed = scroll_speed
        self.logo_path = logo_path if logo_path and os.path.exists(logo_path) else None

    def download_video(self, media_item: MediaItem, output_filename: str) -> bool:
        logger.debug(f"Downloading {media_item.url} => {output_filename}")
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
                ydl.download([media_item.url])
            exists = os.path.exists(output_filename)
            logger.debug(f"Downloaded => {output_filename}? {exists}")
            return exists
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

    def get_video_duration(self, filename: str) -> float:
        logger.debug(f"Probing duration for {filename}")
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", filename]
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            info = json.loads(result.stdout)
            duration = float(info["format"]["duration"])
            logger.debug(f"Duration of {filename}: {duration:.2f}s")
            return duration
        except Exception as e:
            logger.error(f"Could not read duration for {filename}: {e}")
            return 0.0

    def serialize_media_item(self, media_item: MediaItem, output_file: Optional[str] = None,
                             ftv_shows: Optional[List[dict]] = None) -> bool:
        try:
            if media_item.duration is not None:
                target_duration = media_item.duration
            else:
                original_duration = self.get_video_duration(media_item.source_path)
                target_duration = original_duration * (media_item.length_percent / 100.0)

            final_output = output_file if output_file else tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name

            show_title = ""
            show_byline = ""
            if ftv_shows:
                show = random.choice(ftv_shows)
                show_title = show.get("title", "")
                show_byline = show.get("byline", "")

            temp_path = media_item.source_path
            marquee_path = tempfile.NamedTemporaryFile(delete=False).name

            cmd = self._build_ffmpeg_command(
                temp_path,
                marquee_path,
                final_output,
                target_duration,
                artist=media_item.artist,
                song=media_item.song,
                show_title=show_title,
                show_byline=show_byline
            )

            cmd.insert(-1, "-t")
            cmd.insert(-1, str(target_duration))

            logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode('utf-8', 'ignore')}")
                return False

            media_item.serialized = final_output
            return True

        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if os.path.exists(marquee_path):
                os.remove(marquee_path)

    def _build_ffmpeg_command(self, input_path: str, marquee_path: str,
                              output_path: str, target_duration: float,
                              artist: str = "", song: str = "",
                              show_title: str = "", show_byline: str = "") -> List[str]:
        madmil_disk = "madmil-disk.mp4"
        logo_input = []
        scale_logo = ""
        overlay_logo = "[temp]copy[outv]"

        if os.path.exists(madmil_disk):
            logo_input = ["-stream_loop", "-1", "-i", madmil_disk]
            scale_logo = "[2:v]scale=50:-1[logosize];"
            overlay_logo = "[temp][logosize]overlay=10:10[outv]"
        elif self.logo_path and os.path.exists(self.logo_path):
            logo_input = ["-i", self.logo_path]
            scale_logo = "[2:v]scale=50:-1[logosize];"
            overlay_logo = "[temp][logosize]overlay=10:10[outv]"

        safe_artist = artist.replace("'", "\\'")
        safe_song = song.replace("'", "\\'")
        safe_title = show_title.replace("'", "\\'")
        safe_byline = show_byline.replace("'", "\\'")

        title_overlay = (
            f"[v0]drawtext=text='{safe_title}':"
            "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
            "fontsize=24:fontcolor=cyan:bordercolor=green:borderw=2:"
            "x=(w-text_w)/2:y=15:enable=1[titled];"
            f"[titled]drawtext=text='{safe_byline}':"
            "fontfile=/usr/share/fonts/truetype/unifont/unifont.ttf:"
            "fontsize=10:fontcolor=black:bordercolor=green:borderw=1:"
            "x=(w-text_w)/2:y=35:enable=1[titledbylined];"
        )

        filter_str = (
            f"[0:v]scale={self.base_res},setsar=1,trim=duration={target_duration}[v0];"
            f"{title_overlay}"
            "[1:v]scale=640:100[marq];"
            "[titledbylined][marq]overlay=0:360-100[temp];"
            f"{scale_logo}"
            f"{overlay_logo}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-f", "lavfi",
            "-i",
            f"color=c=black:s=1280x100:d={self.marquee_duration},drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:"
            f"textfile={marquee_path}:fontsize=16:fontcolor=white:y=10:"
            f"x='1280 - mod(t*{self.scroll_speed}, 1280+text_w)':enable=1"
        ] + logo_input + [
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-r", "30", "-vsync", "2",
            "-movflags", "+faststart",
            output_path
        ]

        logger.info("FFmpeg command for manual execution:")
        logger.info(" \\\n".join(cmd))

        return cmd

    def serialize_collection(self, media_items: List[MediaItem]) -> List[Tuple[MediaItem, bool]]:
        results = []
        for item in media_items:
            success = self.serialize_media_item(item)
            results.append((item, success))
        return results

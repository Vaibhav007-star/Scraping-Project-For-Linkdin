"""
Automated Video Editor
Trims blank loading screens, speeds up clips for social media pacing,
and exports high-quality, LinkedIn-compatible H.264 MP4 videos.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Pipeline.Editor")

# Universal MoviePy import adapter for MoviePy 1.x and 2.x
try:
    from moviepy import VideoFileClip, vfx
except ImportError:
    from moviepy.editor import VideoFileClip, vfx


class VideoEditor:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _trim_clip(self, clip, trim_start_sec: float):
        """Trim the first N seconds safely."""
        duration = clip.duration
        if duration <= trim_start_sec:
            logger.warning(
                f"Clip duration ({duration:.2f}s) is shorter than or equal to trim duration ({trim_start_sec}s). Keeping entire clip."
            )
            return clip

        logger.info(f"Trimming first {trim_start_sec:.2f}s (Original duration: {duration:.2f}s)...")
        if hasattr(clip, "with_subclip"):
            # MoviePy 2.x
            return clip.with_subclip(trim_start_sec, duration)
        elif hasattr(clip, "subclip"):
            # MoviePy 1.x
            return clip.subclip(trim_start_sec, duration)
        else:
            logger.warning("No subclip method found; returning original clip.")
            return clip

    def _speed_up_clip(self, clip, speed_factor: float):
        """Accelerate video by speed_factor for crisp social media pacing."""
        if speed_factor == 1.0:
            return clip

        logger.info(f"Applying speed multiplier: {speed_factor:.2f}x...")
        if hasattr(clip, "with_effects") and hasattr(vfx, "MultiplySpeed"):
            # MoviePy 2.x
            return clip.with_effects([vfx.MultiplySpeed(speed_factor)])
        elif hasattr(clip, "with_speed_scaled"):
            return clip.with_speed_scaled(speed_factor)
        elif hasattr(clip, "fx") and hasattr(vfx, "speedx"):
            # MoviePy 1.x
            return clip.fx(vfx.speedx, speed_factor)
        else:
            logger.warning("Speed effect not supported on this MoviePy installation; using original speed.")
            return clip

    def process_video(
        self,
        raw_video_path: Path,
        output_filename: str,
        trim_start_sec: float = 2.0,
        speed_factor: float = 1.25
    ) -> Path:
        """
        Process the raw recording:
        1. Trim the initial blank loading buffer
        2. Speed up by 1.25x
        3. Export as LinkedIn-compatible H.264 / AAC MP4 (yuv420p)
        """
        raw_video_path = Path(raw_video_path)
        if not raw_video_path.exists():
            raise FileNotFoundError(f"Input video not found: {raw_video_path}")

        if not output_filename.endswith(".mp4"):
            output_filename += ".mp4"

        target_path = self.output_dir / output_filename
        logger.info(f"Processing '{raw_video_path.name}' -> '{target_path.name}'...")

        raw_clip = None
        trimmed_clip = None
        final_clip = None

        try:
            raw_clip = VideoFileClip(str(raw_video_path))

            # 1. Trim blank loading screen
            trimmed_clip = self._trim_clip(raw_clip, trim_start_sec)

            # 2. Speed up
            final_clip = self._speed_up_clip(trimmed_clip, speed_factor)

            # 3. Export with LinkedIn specifications:
            # - Codec: libx264 (H.264)
            # - Pixel format: yuv420p (universally supported by LinkedIn web/mobile)
            # - Audio: aac (if audio present) or None
            has_audio = final_clip.audio is not None
            audio_codec = "aac" if has_audio else None

            logger.info(f"Rendering final MP4 to {target_path} (H.264, yuv420p)...")
            final_clip.write_videofile(
                str(target_path),
                codec="libx264",
                audio_codec=audio_codec,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                preset="fast",
                threads=4,
                logger=None  # Suppress verbose terminal progress bar
            )

            logger.info(f"Video exported successfully: {target_path} (Duration: {final_clip.duration:.2f}s)")
            return target_path

        finally:
            # Safely release clips and file locks
            for clip in [final_clip, trimmed_clip, raw_clip]:
                if clip is not None:
                    try:
                        clip.close()
                    except Exception:
                        pass

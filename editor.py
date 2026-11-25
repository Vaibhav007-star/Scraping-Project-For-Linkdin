"""
Automated Video Editor & Post-Production Suite
Trims blank loading screens, speeds up clips for social media pacing,
generates free neural AI voiceover via edge-tts, renders synchronized subtitles,
applies professional LinkedIn branding overlays, and exports broadcast-grade H.264 MP4 videos.
"""

import os
import logging
import textwrap
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from voiceover import VoiceoverEngine

logger = logging.getLogger("Pipeline.Editor")

# Universal MoviePy import adapter for MoviePy 1.x and 2.x
try:
    from moviepy import VideoFileClip, vfx
except ImportError:
    from moviepy.editor import VideoFileClip, vfx


def _load_system_fonts() -> Dict[str, ImageFont.ImageFont]:
    """Load crisp system fonts (Segoe UI or Arial) for broadcast-grade typography."""
    candidates = [
        ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeui.ttf"),
        ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"),
    ]
    for bold_p, reg_p in candidates:
        if os.path.exists(bold_p) and os.path.exists(reg_p):
            try:
                return {
                    "title": ImageFont.truetype(bold_p, 16),
                    "sub": ImageFont.truetype(reg_p, 13),
                    "badge": ImageFont.truetype(bold_p, 12),
                    "badge_sub": ImageFont.truetype(reg_p, 12),
                    "hook_title": ImageFont.truetype(bold_p, 14),
                    "hook_sub": ImageFont.truetype(reg_p, 12),
                    "subtitle": ImageFont.truetype(bold_p, 15),
                }
            except Exception:
                pass

    def_f = ImageFont.load_default()
    return {
        "title": def_f,
        "sub": def_f,
        "badge": def_f,
        "badge_sub": def_f,
        "hook_title": def_f,
        "hook_sub": def_f,
        "subtitle": def_f,
    }


class VideoEditor:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fonts = _load_system_fonts()
        self.voiceover_engine = VoiceoverEngine(self.output_dir / "cache")

    def _trim_clip(self, clip, trim_start_sec: float):
        """Trim the first N seconds safely and automatically bypass blank/white loading screens."""
        duration = clip.duration
        effective_trim = max(0.0, trim_start_sec)

        # Automatic blank/white frame bypass: scan forward if still blank
        try:
            check_t = effective_trim
            while check_t < min(duration, 15.0):
                frame = clip.get_frame(check_t)
                mean_lum = float(np.mean(frame))
                if mean_lum > 240.0:  # Pure white blank loading screen
                    check_t += 0.1
                else:
                    break
            if check_t > effective_trim:
                logger.info(f"Detected blank/white loading buffer up to {check_t:.2f}s. Adjusting trim point to {check_t:.2f}s.")
                effective_trim = round(check_t, 2)
        except Exception as e:
            logger.debug(f"Blank detection check skipped: {e}")

        if duration <= effective_trim:
            logger.warning(
                f"Clip duration ({duration:.2f}s) is shorter than or equal to trim duration ({effective_trim:.2f}s). Keeping entire clip."
            )
            return clip

        logger.info(f"Trimming first {effective_trim:.2f}s (Original duration: {duration:.2f}s)...")
        if hasattr(clip, "with_subclip"):
            return clip.with_subclip(effective_trim, duration)
        elif hasattr(clip, "subclip"):
            return clip.subclip(effective_trim, duration)
        else:
            logger.warning("No subclip method found; returning original clip.")
            return clip

    def _speed_up_clip(self, clip, speed_factor: float):
        """Accelerate video by speed_factor for crisp social media pacing."""
        if speed_factor == 1.0:
            return clip

        logger.info(f"Applying speed multiplier: {speed_factor:.2f}x...")
        if hasattr(clip, "with_effects") and hasattr(vfx, "MultiplySpeed"):
            return clip.with_effects([vfx.MultiplySpeed(speed_factor)])
        elif hasattr(clip, "with_speed_scaled"):
            return clip.with_speed_scaled(speed_factor)
        elif hasattr(clip, "fx") and hasattr(vfx, "speedx"):
            return clip.fx(vfx.speedx, speed_factor)
        else:
            logger.warning("Speed effect not supported on this MoviePy installation; using original speed.")
            return clip

    def _resolve_project_branding(self, project_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract and format title, tech stack, and phase badges for video overlay."""
        cfg = project_config or {}
        name = cfg.get("name", "ai_platform")
        title = cfg.get("title", name.replace("_", " ").title())

        # Clean title for top bar display
        short_title = title.split("(")[0].strip()
        if len(short_title) > 38:
            short_title = short_title[:36] + "..."

        # Determine tech stack string
        tech_tags = cfg.get("tech_stack")
        if not tech_tags:
            if "urban_heat" in name:
                tech_tags = "PyTorch U-Net  •  Three.js 3D WebGL  •  FastAPI"
            elif "homemind" in name:
                tech_tags = "Multi-Agent Systems  •  Three.js 3D WebGL  •  FastAPI"
            elif "ai_attendance" in name or "attendance" in name:
                tech_tags = "FastAPI  •  OpenCV Computer Vision  •  128-D Biometric Embeddings"
            elif "firecast" in name or "wildfire" in name:
                tech_tags = "PyTorch PINN  •  Three.js 3D WebGL  •  NASA FIRMS Satellites"
            elif "supply_chain" in name or "control_tower" in name or "risk" in name:
                tech_tags = "FastAPI  •  Scikit-Learn Calibrated Pipeline  •  Operations Control Tower"
            elif "schoolmind" in name or "school" in name:
                tech_tags = "LangGraph  •  FastAPI  •  Three.js 3D WebGL  •  SQLAlchemy"
            elif "churn" in name:
                tech_tags = "XGBoost  •  SHAP Explainability  •  Streamlit"
            else:
                tech_tags = "Deep Learning  •  Computer Vision  •  FastAPI"

        # Determine dynamic phases
        if "urban_heat" in name:
            phases: List[Tuple[float, str, Tuple[int, int, int]]] = [
                (0.12, "1/6 ARCHITECTURE • System Framing & Problem Context", (56, 189, 248)),       # Cyan
                (0.32, "2/6 SATELLITE VISION • PyTorch U-Net Inference & Masks", (16, 185, 129)),     # Emerald
                (0.56, "3/6 3D DIGITAL TWIN • Cinematic Camera Orbit & Heights", (168, 85, 247)),    # Purple
                (0.72, "4/6 THERMAL REGRESSION • ANN Surface Temp Forecast", (245, 158, 11)),         # Amber
                (0.86, "5/6 MITIGATION SIMULATOR • Counterfactual Greening", (16, 185, 129)),         # Emerald
                (1.00, "6/6 MODEL ANALYTICS • Convergence Curves & Metrics", (56, 189, 248)),         # Cyan
            ]
        elif "homemind" in name:
            phases = [
                (0.18, "1/5 MULTI-AGENT TEAM • 5 Specialized Autonomous Agents", (56, 189, 248)),    # Cyan
                (0.38, "2/5 EVENT BUS & MATRIX • Pub-Sub Communication Protocol", (16, 185, 129)),   # Emerald
                (0.58, "3/5 AUTONOMOUS SCENARIOS • Multi-Agent Conflict Resolution", (168, 85, 247)),# Purple
                (0.82, "4/5 3D DIGITAL TWIN • WebGL Utility Overlays & Orbit", (245, 158, 11)),       # Amber
                (1.00, "5/5 EXPLAINABILITY & CHAT • Natural Language Delegation", (16, 185, 129)),    # Emerald
            ]
        elif "ai_attendance" in name or "attendance" in name:
            phases = [
                (0.18, "1/5 SYSTEM ARCHITECTURE • Enterprise Biometric Platform", (56, 189, 248)),    # Cyan
                (0.40, "2/5 ATTENDANCE ANALYTICS • Real-Time Velocity & Punctuality", (16, 185, 129)),# Emerald
                (0.60, "3/5 AUTONOMOUS KIOSK • Multi-Tier Anti-Spoofing & Liveness", (168, 85, 247)), # Purple
                (0.80, "4/5 128-D EMBEDDINGS • L2 Hypersphere Cosine Matching", (245, 158, 11)),      # Amber
                (1.00, "5/5 AUDIT & COMPLIANCE • Automated Shift Enforcement", (16, 185, 129)),       # Emerald
            ]
        elif "firecast" in name or "wildfire" in name:
            phases = [
                (0.18, "1/5 SYSTEM ARCHITECTURE • Physics-Informed Neural Network", (56, 189, 248)),   # Cyan
                (0.38, "2/5 SATELLITE TELEMETRY • NASA MODIS & VIIRS 375m Ingestion", (16, 185, 129)), # Emerald
                (0.58, "3/5 MULTI-HORIZON SPREAD • +12h, +24h, +48h Isochrone Forecasting", (168, 85, 247)),# Purple
                (0.80, "4/5 3D DIGITAL TWIN • Topography Shading & Camera Orbit", (245, 158, 11)),      # Amber
                (1.00, "5/5 WUI VULNERABILITY • Evacuation & Critical Grid Hazard", (16, 185, 129)),    # Emerald
            ]
        elif "supply_chain" in name or "control_tower" in name or "risk" in name:
            phases = [
                (0.18, "1/5 SYSTEM ARCHITECTURE • Relational SQLite DW & Leak-Free ABT", (56, 189, 248)),   # Cyan
                (0.38, "2/5 MLOPS BENCHMARK • Calibrated Classifier & 13% Threshold", (16, 185, 129)),      # Emerald
                (0.58, "3/5 DISPATCH CONTROL TOWER • High-Risk Prioritized Manifest", (168, 85, 247)),       # Purple
                (0.80, "4/5 WHAT-IF SIMULATION • Warehouse Turnaround Sensitivity", (245, 158, 11)),        # Amber
                (1.00, "5/5 ROOT-CAUSE ATTRIBUTION • Tree SHAP & ROI Optimization", (16, 185, 129)),         # Emerald
            ]
        elif "schoolmind" in name or "school" in name:
            phases = [
                (0.18, "1/5 MULTI-AGENT ARCHITECTURE • 7 Collaborative AI Agents", (56, 189, 248)),        # Cyan
                (0.38, "2/5 3D DIGITAL TWIN • Three.js WebGL Campus & Neural Galaxy", (16, 185, 129)),     # Emerald
                (0.58, "3/5 6AM CRISIS SCENARIO • Autonomous Sub & Room Relocation", (168, 85, 247)),       # Purple
                (0.80, "4/5 STUDENT INTERVENTION • Early Academic Risk Regression", (245, 158, 11)),        # Amber
                (1.00, "5/5 CAMPUS SAFETY & HITL • Access Control & FERPA Audit", (16, 185, 129)),          # Emerald
            ]
        else:
            phases = [
                (0.15, "1/5 SYSTEM ARCHITECTURE • Problem Framing & Tech Stack", (56, 189, 248)),
                (0.40, "2/5 MODEL INFERENCE • Live AI Pipeline Execution", (16, 185, 129)),
                (0.65, "3/5 MULTI-VIEW ANALYSIS • Interactive Visualizations", (168, 85, 247)),
                (0.85, "4/5 PARAMETER SIMULATION • Dynamic Sliders & Scenarios", (245, 158, 11)),
                (1.00, "5/5 VALIDATION BENCHMARKS • Quantitative Performance", (56, 189, 248)),
            ]

        if "homemind" in name:
            hook_sub = "Autonomous Multi-Agent AI Ecosystem & 3D Digital Twin"
        elif "ai_attendance" in name or "attendance" in name:
            hook_sub = "Enterprise Facial Biometric Platform & Anti-Spoofing Engine"
        elif "firecast" in name or "wildfire" in name:
            hook_sub = "Physics-Informed Wildfire Intelligence & 3D Digital Twin"
        elif "supply_chain" in name or "control_tower" in name or "risk" in name:
            hook_sub = "Supply Chain Risk Control Tower & What-If Logistics Simulator"
        elif "schoolmind" in name or "school" in name:
            hook_sub = "Autonomous Multi-Agent AI School Management System & 3D Twin"
        else:
            hook_sub = "Deep Learning Pipeline & Real-Time Interactive Simulation"

        return {
            "title": short_title.upper(),
            "tech_tags": tech_tags,
            "phases": phases,
            "hook_title": "LIVE PRODUCTION WALKTHROUGH",
            "hook_sub": hook_sub,
        }

    def _apply_linkedin_branding(
        self,
        clip,
        project_config: Optional[Dict[str, Any]] = None,
        subtitles: Optional[List[Tuple[float, float, str]]] = None
    ):
        """
        Applies automated professional LinkedIn post-production graphics:
        1. Zero-Navbar-Occlusion: Leaves top 100% unobstructed so app navigation tabs are fully visible.
        2. Dynamic Lower-Third Badge: Contextual phase callout that updates with video progress.
        3. Synchronized Closed Captions: Modern subtitle pill rendered during speech.
        4. Animated Progress Bar: Sleek 5px glowing accent bar tracking elapsed playback time.
        5. Intro Hook Overlay: 3-second floating hero card at lower-left with smooth alpha fade-out.
        """
        logger.info("Applying automated LinkedIn post-production graphics with zero-navbar-occlusion...")
        w, h = clip.size
        duration = clip.duration
        branding = self._resolve_project_branding(project_config)
        fonts = self.fonts
        active_subtitles = subtitles or []

        phases = branding["phases"]
        hook_title = branding["hook_title"]
        hook_sub = branding["hook_sub"]

        def frame_transformer(get_frame, t: float) -> np.ndarray:
            frame = get_frame(t)
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img, "RGBA")

            ratio = min(1.0, max(0.0, t / (duration + 1e-5)))

            # ---------------------------------------------------------
            # ZERO TOP OCCLUSION:
            # The top navigation bar, logo, and tabs remain 100% pristine!
            # ---------------------------------------------------------

            # ---------------------------------------------------------
            # 1. Dynamic Lower-Third Feature Badge (Bottom-Left)
            # ---------------------------------------------------------
            current_badge = phases[-1][1]
            current_color = phases[-1][2]
            for end_r, badge_txt, color in phases:
                if ratio <= end_r:
                    current_badge = badge_txt
                    current_color = color
                    break

            bx1, by1 = 24, h - 46
            badge_bbox = fonts["badge"].getbbox(current_badge)
            badge_text_w = badge_bbox[2] - badge_bbox[0] if badge_bbox else 400
            badge_w = max(420, badge_text_w + 44)
            bx2, by2 = bx1 + badge_w, by1 + 32

            draw.rounded_rectangle(
                [bx1, by1, bx2, by2],
                radius=6,
                fill=(9, 13, 22, 235),
                outline=(51, 65, 85, 255),
                width=1
            )
            # Active phase colored indicator dot
            draw.ellipse([bx1 + 10, by1 + 11, bx1 + 20, by1 + 21], fill=current_color)
            draw.text((bx1 + 28, by1 + 7), current_badge, fill=(241, 245, 249, 255), font=fonts["badge"])

            # ---------------------------------------------------------
            # 2. Synchronized Closed Captions / Subtitles (Bottom-Center)
            # ---------------------------------------------------------
            if active_subtitles:
                current_sub = None
                for s_start, s_end, s_txt in active_subtitles:
                    if s_start <= t <= s_end:
                        current_sub = s_txt.strip()
                        break

                if current_sub:
                    wrapped_lines = textwrap.wrap(current_sub, width=64)
                    line_height = 24
                    sub_h = (len(wrapped_lines) * line_height) + 16

                    max_line_w = 0
                    for line in wrapped_lines:
                        lbox = fonts["subtitle"].getbbox(line)
                        if lbox:
                            max_line_w = max(max_line_w, lbox[2] - lbox[0])
                    sub_w = max(380, max_line_w + 36)

                    # Center subtitle horizontally, place comfortably above lower badges
                    sx1 = int((w - sub_w) / 2.0)
                    sy1 = h - sub_h - 22
                    sx2 = sx1 + sub_w
                    sy2 = sy1 + sub_h

                    draw.rounded_rectangle(
                        [sx1, sy1, sx2, sy2],
                        radius=8,
                        fill=(9, 13, 22, 235),
                        outline=(51, 65, 85, 255),
                        width=1
                    )
                    for l_idx, line in enumerate(wrapped_lines):
                        ly = sy1 + 8 + (l_idx * line_height)
                        lbox = fonts["subtitle"].getbbox(line)
                        lw = lbox[2] - lbox[0] if lbox else 200
                        lx = sx1 + int((sub_w - lw) / 2.0)
                        # Warm bright yellow font for crisp readability
                        draw.text((lx, ly), line, fill=(254, 240, 138, 255), font=fonts["subtitle"])

            # ---------------------------------------------------------
            # 3. Intro Recruiter Hook Card (First 3.2 seconds - Lower-Left)
            # ---------------------------------------------------------
            if t <= 3.2:
                # Alpha fade-out calculation (smooth fade from t=2.3s to 3.2s)
                alpha = 1.0 if t < 2.3 else max(0.0, 1.0 - ((t - 2.3) / 0.9))
                if alpha > 0.02:
                    hx1, hy1 = 24, h - 110
                    hx2, hy2 = hx1 + 470, hy1 + 54
                    fill_alpha = int(240 * alpha)
                    border_alpha = int(255 * alpha)
                    text_alpha = int(255 * alpha)
                    sub_alpha = int(200 * alpha)

                    draw.rounded_rectangle(
                        [hx1, hy1, hx2, hy2],
                        radius=8,
                        fill=(15, 23, 42, fill_alpha),
                        outline=(56, 189, 248, border_alpha),
                        width=1
                    )
                    draw.text(
                        (hx1 + 16, hy1 + 10),
                        f"🚀  {hook_title}",
                        fill=(56, 189, 248, text_alpha),
                        font=fonts["hook_title"]
                    )
                    draw.text(
                        (hx1 + 16, hy1 + 30),
                        hook_sub,
                        fill=(226, 232, 240, sub_alpha),
                        font=fonts["hook_sub"]
                    )

            # ---------------------------------------------------------
            # 4. Animated Bottom Progress Bar (5px)
            # ---------------------------------------------------------
            draw.rectangle([0, h - 5, w, h], fill=(15, 23, 42, 200))
            prog_w = int(w * ratio)
            if prog_w > 0:
                draw.rectangle([0, h - 5, prog_w, h], fill=(16, 185, 129, 255))

            return np.array(img)

        # Apply transformation across the video clip
        if hasattr(clip, "transform"):
            return clip.transform(frame_transformer)
        else:
            return clip

    def process_video(
        self,
        raw_video_path: Path,
        output_filename: str,
        trim_start_sec: float = 2.0,
        speed_factor: float = 1.25,
        project_config: Optional[Dict[str, Any]] = None,
        enable_branding: bool = True,
        enable_voiceover: bool = True
    ) -> Path:
        """
        Process the raw recording with Option C Automated Code-Based Editing:
        1. Trim the initial blank loading buffer
        2. Speed up by speed_factor (e.g. 1.18x)
        3. Synthesize neural AI voiceover and sentence boundaries via edge-tts
        4. Apply professional LinkedIn branding overlays + synchronized captions
        5. Composite voiceover audio track
        6. Export as broadcast-grade LinkedIn-compatible H.264 / AAC MP4 (yuv420p)
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
        sped_clip = None
        branded_clip = None
        final_clip = None
        audio_clip = None

        try:
            raw_clip = VideoFileClip(str(raw_video_path))

            # 1. Trim blank loading screen
            trimmed_clip = self._trim_clip(raw_clip, trim_start_sec)

            # 2. Speed up
            sped_clip = self._speed_up_clip(trimmed_clip, speed_factor)

            # 3. Build Neural AI Voiceover & Subtitles (if enabled)
            subtitles = []
            if enable_voiceover and project_config:
                try:
                    audio_clip, subtitles = self.voiceover_engine.build_voiceover_and_subtitles(
                        project_config=project_config,
                        video_duration=sped_clip.duration
                    )
                except Exception as ve:
                    logger.warning(f"Voiceover generation skipped due to: {ve}")

            # 4. Apply Automated Professional LinkedIn Post-Production Overlays & Subtitles
            if enable_branding:
                branded_clip = self._apply_linkedin_branding(
                    sped_clip,
                    project_config=project_config,
                    subtitles=subtitles
                )
            else:
                branded_clip = sped_clip

            # 5. Composite audio track
            if audio_clip is not None:
                if hasattr(branded_clip, "with_audio"):
                    final_clip = branded_clip.with_audio(audio_clip)
                elif hasattr(branded_clip, "set_audio"):
                    final_clip = branded_clip.set_audio(audio_clip)
                else:
                    final_clip = branded_clip
            else:
                final_clip = branded_clip

            # 6. Export with LinkedIn specifications:
            # - Codec: libx264 (H.264)
            # - Pixel format: yuv420p
            # - Audio codec: aac
            has_audio = final_clip.audio is not None
            audio_codec = "aac" if has_audio else None

            bitrate = os.getenv("VIDEO_BITRATE", "12M")
            crf = os.getenv("VIDEO_CRF", "18")
            logger.info(f"Rendering final MP4 to {target_path} (H.264, yuv420p, CRF {crf}, Bitrate {bitrate}, Audio: {audio_codec})...")
            
            orig_remove = os.remove
            def safe_remove(p_rem, *args, **kwargs):
                try:
                    orig_remove(p_rem, *args, **kwargs)
                except PermissionError:
                    time.sleep(0.5)
                    try:
                        orig_remove(p_rem, *args, **kwargs)
                    except Exception:
                        pass
                except Exception:
                    pass

            os.remove = safe_remove
            try:
                final_clip.write_videofile(
                    str(target_path),
                    codec="libx264",
                    audio_codec=audio_codec,
                    bitrate=bitrate,
                    ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", str(crf), "-movflags", "+faststart"],
                    preset="medium",
                    threads=4,
                    logger=None  # Suppress verbose terminal progress bar
                )
            finally:
                os.remove = orig_remove

            logger.info(f"Video exported successfully: {target_path} (Duration: {final_clip.duration:.2f}s)")
            return target_path

        finally:
            # Safely release clips and file locks
            for clip in [final_clip, branded_clip, sped_clip, trimmed_clip, raw_clip, audio_clip]:
                if clip is not None:
                    try:
                        clip.close()
                    except Exception:
                        pass

"""
Voiceover & Subtitle Engine
Uses free, open-source edge-tts (Microsoft Neural Speech) to generate
human-like studio narration and synchronized sentence subtitles for AI showcase videos.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import edge_tts

try:
    from moviepy import AudioFileClip, CompositeAudioClip
except ImportError:
    from moviepy.editor import AudioFileClip, CompositeAudioClip

logger = logging.getLogger("Pipeline.Voiceover")

# Default professional neural voice (warm, authoritative American engineering tone)
DEFAULT_VOICE = "en-US-ChristopherNeural"


class VoiceoverEngine:
    def __init__(self, cache_dir: Path, voice: str = DEFAULT_VOICE):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.voice = voice

    async def _synthesize_clip(
        self,
        text: str,
        output_file: Path,
        rate: str = "+2%"
    ) -> List[Tuple[float, float, str]]:
        """Synthesize a single audio file and return its sentence boundaries."""
        comm = edge_tts.Communicate(text.strip(), voice=self.voice, rate=rate)
        subtitles = []

        with open(output_file, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    start_s = chunk["offset"] / 10_000_000.0
                    dur_s = chunk["duration"] / 10_000_000.0
                    subtitles.append((start_s, start_s + dur_s, chunk["text"]))

        return subtitles

    def _get_project_script_sections(
        self,
        project_config: Dict[str, Any],
        total_duration: float
    ) -> List[Dict[str, Any]]:
        """Returns time-aligned narrative sections matching project video tabs."""
        name = project_config.get("name", "")

        if "urban_heat" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "Urban heat islands exacerbate extreme microclimate temperatures in metropolitan sectors like Noida Sector 106. Retrospective thermal analysis alone cannot quantify mitigation benefits before capital is invested."
                },
                {
                    "start_sec": 16.5,
                    "text": "To solve this, our deep learning pipeline ingests high-resolution satellite imagery through a PyTorch U-Net architecture, classifying surface composition into impervious structures, vegetation, and water bodies."
                },
                {
                    "start_sec": 45.0,
                    "text": "The platform projects these land-cover fractions into an interactive 3D digital twin powered by WebGL. Planners can toggle isometric views, scale building heights to 2.3 times, and perform cinematic camera orbits to inspect spatial relief."
                },
                {
                    "start_sec": 73.0,
                    "text": "Next, an Artificial Neural Network correlates land-cover percentages with solar irradiance and humidity to forecast Land Surface Temperature anomalies in real time."
                },
                {
                    "start_sec": 93.0,
                    "text": "Planners can simulate counterfactual urban greening interventions. Ramping canopy coverage from 10 to 35 percent dynamically predicts cooling deltas and local energy savings."
                },
                {
                    "start_sec": 113.0,
                    "text": "Comprehensive validation analytics showcase loss convergence, IoU scores, and confusion matrix reliability, bridging geospatial AI with actionable climate resilience."
                }
            ]
        elif "homemind" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "HomeMind transforms residential automation into an autonomous multi-agent ecosystem. Five specialized AI agents collaborate within a shared home context to observe, reason, and actuate home systems."
                },
                {
                    "start_sec": 16.0,
                    "text": "The platform orchestrates Home Manager, Energy Guard, Climate Sentinel, Aqua Guard, and Perimeter Sentry across a distributed event bus, synchronizing real-time telemetry and state changes."
                },
                {
                    "start_sec": 38.0,
                    "text": "During autonomous scenarios like morning wakeups or water leaks, agents exchange structured messages, resolving conflicting priorities and generating explainable decision rationales."
                },
                {
                    "start_sec": 58.0,
                    "text": "Transitioning to the 3D dollhouse digital twin powered by Three.js and WebGL. Operators can inspect live electrical and plumbing utility overlays, rotate perspectives, and focus into individual rooms."
                },
                {
                    "start_sec": 82.0,
                    "text": "Residents can delegate complex tasks through natural language or inspect explainability trees, demonstrating how collaborative agent architectures unlock truly intelligent spatial computing."
                }
            ]
        elif "ai_attendance" in name or "attendance" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "VisionAttend AI transforms enterprise workforce management through autonomous facial biometrics, combining high-speed edge computer vision with zero-contact attendance intelligence."
                },
                {
                    "start_sec": 16.0,
                    "text": "The executive analytics dashboard tracks real-time workforce attendance velocity, shift punctuality curves, and department breakdowns, backed by an SQLite persistence engine."
                },
                {
                    "start_sec": 36.0,
                    "text": "The autonomous face kiosk continuously scans incoming video feeds. Multi-tier anti-spoofing pairs Laplacian texture variance with 2D FFT frequency analysis to defeat screen and print replay attacks."
                },
                {
                    "start_sec": 54.0,
                    "text": "Dense 128-dimensional biometric embeddings are normalized onto an L2 hypersphere, executing sub-120 millisecond cosine similarity searches against an in-memory RAM cache."
                },
                {
                    "start_sec": 72.0,
                    "text": "Comprehensive verification records enforce automated shift schedules and anti-passback cooldowns, delivering audit-ready workforce telemetry with complete biometric integrity."
                }
            ]
        elif "firecast" in name or "wildfire" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "Wildfires exhibit complex non-linear physical spread driven by wind advection and steep elevation gradients. Conventional empirical models struggle to capture multi-horizon perimeter dynamics in real time."
                },
                {
                    "start_sec": 16.0,
                    "text": "FIRECAST AI couples Physics-Informed Neural Networks with real NASA satellite telemetry. The architecture enforces 2D advection-diffusion conservation laws alongside Rothermel reaction kinetics on an RTX GPU."
                },
                {
                    "start_sec": 38.0,
                    "text": "The synchronized horizon view projects 12-hour, 24-hour, and 48-hour fire arrival isochrones across 6 spatiotemporal channels, fusing Sentinel-2 NDVI canopy with digital elevation topography."
                },
                {
                    "start_sec": 58.0,
                    "text": "Transitioning to the 3D digital twin. Operators inspect procedural topography shading, wireframe mesh contours, and volumetric smoke particles with cinematic mouse-driven camera orbits."
                },
                {
                    "start_sec": 78.0,
                    "text": "Monte Carlo dropout maps quantify epistemic uncertainty, while the WUI vulnerability engine pinpoints critical electrical grid, water reservoir, and evacuation route hazards."
                }
            ]
        else:
            title = project_config.get("title", name.replace("_", " ").title())
            p1 = f"Welcome to the demonstration of the {title}. This platform integrates modern machine learning architectures into an end-to-end interactive decision environment."
            p2 = "The neural pipeline executes real-time inference across incoming data streams, extracting latent features and high-dimensional predictions."
            p3 = "Interactive controls and visualizations allow engineers to stress-test parameters, observe model sensitivity, and review counterfactual scenario outcomes."
            p4 = "Rigorous validation benchmarks and telemetry demonstrate training convergence, precision, and operational reliability."

            # Evenly space 4 paragraphs across the video duration
            gap = total_duration / 4.0
            return [
                {"start_sec": 1.5, "text": p1},
                {"start_sec": max(12.0, gap), "text": p2},
                {"start_sec": max(25.0, gap * 2.0), "text": p3},
                {"start_sec": max(40.0, gap * 3.0), "text": p4},
            ]

    def build_voiceover_and_subtitles(
        self,
        project_config: Dict[str, Any],
        video_duration: float
    ) -> Tuple[Optional[Any], List[Tuple[float, float, str]]]:
        """
        Synthesizes all audio sections, composites them at precise timestamps,
        and returns the CompositeAudioClip along with global subtitle timestamps.
        """
        sections = self._get_project_script_sections(project_config, video_duration)
        project_name = project_config.get("name", "project")
        audio_dir = self.cache_dir / f"audio_{project_name}"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_clips = []
        global_subtitles = []

        logger.info(f"Generating neural voiceover ({self.voice}) across {len(sections)} sections...")

        for idx, sec in enumerate(sections):
            start_t = sec["start_sec"]
            text = sec["text"]
            mp3_path = audio_dir / f"section_{idx + 1}.mp3"

            # Synthesize via edge-tts
            try:
                local_subs = asyncio.run(self._synthesize_clip(text, mp3_path))
                logger.info(f"  [Voiceover {idx + 1}/{len(sections)}] Start: {start_t:.1f}s -> {mp3_path.name}")

                # Load as AudioFileClip and position at start_t
                aclip = AudioFileClip(str(mp3_path))
                if hasattr(aclip, "with_start"):
                    positioned_clip = aclip.with_start(start_t)
                elif hasattr(aclip, "set_start"):
                    positioned_clip = aclip.set_start(start_t)
                else:
                    positioned_clip = aclip

                audio_clips.append(positioned_clip)

                # Offset local subtitle timestamps to global video timestamps
                for s_start, s_end, s_text in local_subs:
                    global_subtitles.append((start_t + s_start, start_t + s_end, s_text))

            except Exception as e:
                logger.warning(f"Could not generate voiceover for section {idx + 1}: {e}")

        if not audio_clips:
            return None, []

        try:
            composite = CompositeAudioClip(audio_clips)
            return composite, global_subtitles
        except Exception as e:
            logger.error(f"Failed to composite audio clips: {e}")
            return None, global_subtitles

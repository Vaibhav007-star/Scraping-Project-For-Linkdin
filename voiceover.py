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
        elif "supply_chain" in name or "control_tower" in name or "risk" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "In high-volume e-commerce fulfillment, delivery delays erode customer lifetime value and spike appeasement overhead. Traditional post-mortem analytics identify failures only after packages are already late."
                },
                {
                    "start_sec": 16.0,
                    "text": "This Supply Chain Operations Control Tower ingests millions of relational records into an Analytical Base Table with zero lookahead bias, engineering Haversine transit distances and expanding Bayesian seller reliability scores."
                },
                {
                    "start_sec": 36.0,
                    "text": "The prioritized holdout manifest ranks outbound consignments by calibrated delay risk. Dispatch teams filter critical cross-state parcels, targeting warehouse intervention before carrier handoff occurs."
                },
                {
                    "start_sec": 54.0,
                    "text": "The interactive What-If turnaround simulator models fulfillment acceleration in real time, proving that saving 24 hours of warehouse processing lag slashes customer delivery delay risk by over 45%."
                },
                {
                    "start_sec": 74.0,
                    "text": "Model governance benchmarks Random Forest and gradient boosters under Platt probability calibration, while Tree SHAP attribution highlights distance and dispatch bottlenecks across an optimal 13% decision threshold."
                }
            ]
        elif "schoolmind" in name or "school" in name:
            return [
                {
                    "start_sec": 1.2,
                    "text": "Modern educational institutions struggle with fragmented administrative silos, late-stage student dropout intervention, and chaotic morning teacher absence coverage."
                },
                {
                    "start_sec": 16.0,
                    "text": "SchoolMind orchestrates seven specialized autonomous agents over a pub-sub blackboard event bus, synchronizing academic risk, substitute teacher allocation, facility health, and premise security."
                },
                {
                    "start_sec": 36.0,
                    "text": "Transitioning to the 3D Studio powered by Three.js and WebGL. Administrators can inspect architectural classroom layouts, HVAC load maps, and the 10-agent neural galaxy with smooth camera orbits."
                },
                {
                    "start_sec": 56.0,
                    "text": "During complex scenarios like the 6AM Crisis, agents autonomously balance substitute teacher credentials, relocate lab classes based on equipment needs, and draft FERPA-compliant communications."
                },
                {
                    "start_sec": 76.0,
                    "text": "Early warning regression models track attendance decay and grade trends, routing high-impact interventions to human principals through a verifiable, explainable decision tree."
                }
            ]
        elif "recosphere" in name or "two_tower" in name:
            return [
                {
                    "start_sec": 1.5,
                    "text": "RecoSphere AI is a production two-tower deep recommendation platform trained on 2.75 million Retailrocket e-commerce interactions."
                },
                {
                    "start_sec": 12.0,
                    "text": "Separate user and item deep neural towers project shoppers and catalog products into a shared 64-dimensional metric space for sub-5 millisecond vector retrieval."
                },
                {
                    "start_sec": 23.0,
                    "text": "The multi-signal re-ranking engine balances semantic relevance, popularity bias, and category affinity with Maximal Marginal Relevance diversification."
                },
                {
                    "start_sec": 34.0,
                    "text": "A built-in Monte-Carlo A/B testing simulator executes two-proportion Z-tests and bootstrap confidence intervals to validate statistical uplift."
                }
            ]
        elif "insightflow" in name or "insight_flow" in name:
            return [
                {
                    "start_sec": 1.5,
                    "text": "InsightFlow AI is a multi-agent data analyst platform that converts natural language business questions into verified SQL and interactive visualizations."
                },
                {
                    "start_sec": 12.0,
                    "text": "Eight specialized autonomous agents collaborate from schema discovery and query intent to read-only SQL compilation and security guardrail validation."
                },
                {
                    "start_sec": 22.5,
                    "text": "The platform analyzes over 1,200 Kaggle Superstore transactions, generating Recharts visual encodings alongside real-time statistical anomaly detection."
                },
                {
                    "start_sec": 33.0,
                    "text": "Business leaders can inspect execution plans, run what-if scenario simulations, and review comprehensive model evaluation benchmarks."
                }
            ]
        elif "land_acquisition" in name:
            return [
                {
                    "start_sec": 1.5,
                    "text": "The Ministry of Rural Development platform predicts land acquisition bottlenecks across India's central infrastructure portfolio."
                },
                {
                    "start_sec": 11.5,
                    "text": "Calibrated gradient boosting achieves point 94 ROC-AUC on 1,477 authentic MoSPI and PMGSY project records."
                },
                {
                    "start_sec": 21.5,
                    "text": "Interactive geospatial maps, 3D corridor twins, and policy sandboxes model right-of-way friction and counterfactual intervention."
                },
                {
                    "start_sec": 31.5,
                    "text": "Contagion networks and automated RFCTLARR 2013 statutory tracking prevent cascading delay shocks and legal lapses."
                }
            ]
        else:
            raw_title = project_config.get("title", name.replace("_", " ").title())
            title = raw_title.split("—")[0].split("(")[0].strip()
            if len(title) > 35:
                title = title[:32] + "..."
            p1 = f"Welcome to the demonstration of {title}, an interactive decision-support and machine learning system."
            p2 = "The AI pipeline executes real-time inference across incoming data streams, extracting latent features and risk predictions."
            p3 = "Interactive controls allow engineers to stress-test parameters, observe model sensitivity, and review counterfactual scenario outcomes."
            p4 = "Rigorous validation benchmarks and telemetry demonstrate quantitative reliability and operational performance."

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
        Guarantees strict zero-collision spacing between audio clips.
        """
        sections = self._get_project_script_sections(project_config, video_duration)
        project_name = project_config.get("name", "project")
        audio_dir = self.cache_dir / f"audio_{project_name}"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_clips = []
        global_subtitles = []
        current_cursor = 0.0
        min_silence_gap = 1.0  # Guarantee at least 1.0s silence between spoken thoughts

        logger.info(f"Generating neural voiceover ({self.voice}) across {len(sections)} sections...")

        for idx, sec in enumerate(sections):
            requested_start_t = sec["start_sec"]
            text = sec["text"]
            mp3_path = audio_dir / f"section_{idx + 1}.mp3"

            # Synthesize via edge-tts
            try:
                local_subs = asyncio.run(self._synthesize_clip(text, mp3_path))
                aclip = AudioFileClip(str(mp3_path))
                dur = aclip.duration

                # Enforce no collision: clip must not start before previous clip ends + min_silence_gap
                actual_start_t = max(requested_start_t, current_cursor + min_silence_gap)

                # Ensure clip doesn't overflow past video duration
                if actual_start_t + dur > video_duration:
                    actual_start_t = max(current_cursor + 0.4, min(actual_start_t, max(0.0, video_duration - dur - 0.3)))

                logger.info(f"  [Voiceover {idx + 1}/{len(sections)}] Requested: {requested_start_t:.1f}s -> Actual: {actual_start_t:.1f}s (dur: {dur:.2f}s) -> {mp3_path.name}")

                if hasattr(aclip, "with_start"):
                    positioned_clip = aclip.with_start(actual_start_t)
                elif hasattr(aclip, "set_start"):
                    positioned_clip = aclip.set_start(actual_start_t)
                else:
                    positioned_clip = aclip

                audio_clips.append(positioned_clip)

                # Offset local subtitle timestamps to actual global video timestamps
                for s_start, s_end, s_text in local_subs:
                    global_subtitles.append((actual_start_t + s_start, actual_start_t + s_end, s_text))

                current_cursor = actual_start_t + dur

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
        except Exception as e:
            logger.error(f"Failed to composite audio clips: {e}")
            return None, global_subtitles

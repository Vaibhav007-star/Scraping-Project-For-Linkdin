"""
Project Runner & AI-Vision Guided Screen Recorder
Features a multimodal Gemini Vision Director that visually analyzes UI screenshots,
identifies primary interactive features, and orchestrates an engaging, humanized showcase tour
(at least 30 seconds long) with smooth animated cursor movements, clicks, and chart walkthroughs.
"""

import os
import re
import json
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.error

import psutil
from playwright.sync_api import sync_playwright

logger = logging.getLogger("Pipeline.Recorder")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# Animated cursor overlay so LinkedIn viewers see mouse tracking and click feedback
CURSOR_INJECTION_SCRIPT = """
(function() {
    if (document.getElementById('playwright-demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'playwright-demo-cursor';
    cursor.style.cssText = `
        width: 22px;
        height: 22px;
        background: rgba(239, 68, 68, 0.85);
        border: 2px solid #ffffff;
        border-radius: 50%;
        position: fixed;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: 2147483647;
        transition: transform 0.12s cubic-bezier(0.2, 0, 0, 1), background-color 0.15s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        transform: translate(-50%, -50%);
    `;
    document.documentElement.appendChild(cursor);

    window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    }, { passive: true });

    window.addEventListener('mousedown', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.6)';
        cursor.style.backgroundColor = 'rgba(16, 185, 129, 0.95)';
    }, { passive: true });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.0)';
        cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.85)';
    }, { passive: true });
})();
"""


class ProjectRecorder:
    def __init__(self, raw_recordings_dir: Path):
        self.raw_recordings_dir = Path(raw_recordings_dir)
        self.raw_recordings_dir.mkdir(parents=True, exist_ok=True)
        self.gemini_client = None
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and genai is not None:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                logger.info(f"Gemini Vision Director initialized ({self.gemini_model}).")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Vision: {e}")

    def is_live_url(self, url: str) -> bool:
        """Check if URL points to an external cloud deployment (e.g. Vercel) rather than local."""
        return not ("localhost" in url.lower() or "127.0.0.1" in url)

    def _is_server_responsive(self, url: str) -> bool:
        """Check if HTTP server is responding."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status in (200, 301, 302, 404, 403)
        except Exception:
            return False

    def wait_for_server(self, url: str, timeout_sec: int = 30) -> bool:
        """Poll server until available."""
        if self.is_live_url(url):
            logger.info(f"Target is a live cloud deployment ({url}). Skipping local wait.")
            return True

        logger.info(f"Waiting for local server at {url} (up to {timeout_sec}s)...")
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if self._is_server_responsive(url):
                logger.info(f"Server is up and responsive at {url}!")
                return True
            time.sleep(1.0)
        return False

    def start_server(self, project_config: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """Start local server subprocess. If it's a live URL or has no start_command, skips server."""
        url = project_config.get("live_url") or project_config.get("url", "")
        start_cmd = project_config.get("start_command")

        if self.is_live_url(url) or not start_cmd:
            logger.info(f"Project '{project_config.get('name')}' uses live deployment at {url}. No local process required.")
            return None

        project_folder = Path(project_config.get("folder_path", "."))
        if not project_folder.exists():
            raise FileNotFoundError(f"Project folder not found: {project_folder}")

        logger.info(f"Starting local server in '{project_folder}': `{start_cmd}`")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

        return subprocess.Popen(
            start_cmd,
            shell=True,
            cwd=str(project_folder),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )

    def stop_server(self, process: Optional[subprocess.Popen]):
        """Cleanly terminate server and all its child processes."""
        if process is None:
            return

        pid = process.pid
        logger.info(f"Shutting down server process tree (PID: {pid})...")
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

            _, still_alive = psutil.wait_procs(children, timeout=3)
            for child in still_alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass

            parent.terminate()
            parent.wait(timeout=3)
            logger.info(f"Server process {pid} stopped.")
        except Exception as e:
            logger.debug(f"Process termination note: {e}")

    def _get_vision_tour_plan(self, screenshot_bytes: bytes, project_name: str, total_sec: int) -> List[Dict[str, Any]]:
        """
        Uses Gemini Vision to inspect the application screenshot and formulate
        a professional demonstration plan highlighting the best features.
        """
        if not self.gemini_client:
            return []

        prompt = (
            f"You are an expert AI Portfolio Showcase Video Director directing a screen recording of the app '{project_name}'. "
            f"Look at this application UI screenshot (1280x720 resolution). "
            f"Plan a {total_sec}-second sequential feature tour that showcases the most impressive interactive capabilities, "
            f"such as switching between views/tabs, clicking prediction or overlay toggles, hovering over metrics, "
            f"and scrolling down to inspect charts and model outputs.\n\n"
            f"Output ONLY a JSON array of sequential steps with this schema:\n"
            f"[\n"
            f"  {{\"action\": \"hover\", \"x\": 640, \"y\": 150, \"wait_ms\": 1500, \"description\": \"Introduce dashboard header\"}},\n"
            f"  {{\"action\": \"click\", \"x\": 340, \"y\": 220, \"wait_ms\": 3000, \"description\": \"Switch to interactive land-cover tab\"}},\n"
            f"  {{\"action\": \"scroll\", \"delta_y\": 350, \"wait_ms\": 2500, \"description\": \"Scroll to explore thermal heat maps\"}},\n"
            f"  {{\"action\": \"click\", \"x\": 450, \"y\": 220, \"wait_ms\": 3000, \"description\": \"Toggle blended overlay model\"}},\n"
            f"  {{\"action\": \"scroll\", \"delta_y\": 400, \"wait_ms\": 3500, \"description\": \"Showcase neural network architecture and charts\"}}\n"
            f"]\n"
            f"Constraints: Use pixel coordinates within 0..1280 (x) and 0..720 (y). Do not include markdown codeblocks or prose."
        )

        try:
            logger.info(f"Querying Gemini Vision Director ({self.gemini_model}) for '{project_name}' UI tour plan...")
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=screenshot_bytes, mime_type="image/jpeg")
                ]
            )

            if response and response.text:
                cleaned = re.sub(r"^```(?:json)?\s*", "", response.text.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned.strip())
                # Find JSON array bracket
                m = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
                if m:
                    steps = json.loads(m.group(0))
                    logger.info(f"Gemini Vision Director generated {len(steps)} visual tour steps!")
                    return steps
        except Exception as e:
            logger.warning(f"Gemini Vision tour generation note: {e}")

        return []

    def record_session(
        self,
        project_config: Dict[str, Any],
        duration_sec: int = 40
    ) -> Path:
        """
        Records the screen while navigating through features using Vision AI and DOM intelligence.
        Guarantees a comprehensive, multi-feature demonstration lasting >= 30 seconds.
        """
        url = project_config.get("live_url") or project_config.get("url", "http://localhost:8501")
        project_name = project_config.get("name", "project_demo")
        custom_duration = project_config.get("record_duration_seconds", duration_sec)

        temp_record_dir = self.raw_recordings_dir / f"tmp_{project_name}"
        temp_record_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Launching Vision AI-Guided Screen Recording for '{project_name}' ({custom_duration}s target)...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--start-maximized", "--disable-gpu", "--no-sandbox"]
            )

            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(temp_record_dir),
                record_video_size={"width": 1280, "height": 720}
            )

            page = context.new_page()

            try:
                # 1. Navigate to target URL
                logger.info(f"Navigating to {url}...")
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)

                # 2. Inject visible animated cursor overlay
                try:
                    page.evaluate(CURSOR_INJECTION_SCRIPT)
                except Exception:
                    pass

                # 3. Check for explicitly defined interaction rules or use Gemini Vision Director
                start_time = time.time()
                custom_interactions = project_config.get("interactions", [])

                if custom_interactions:
                    logger.info(f"Executing ALL {len(custom_interactions)} curated SCRAPING_RULES interactions for '{project_name}' (Zero Time Limit)...")
                    for idx, step in enumerate(custom_interactions, start=1):
                        action = step.get("action")
                        selector = step.get("selector")
                        wait_ms = step.get("wait_ms", 3000)
                        desc = step.get("description", selector or action)

                        logger.info(f"Interaction {idx}/{len(custom_interactions)}: {action} -> {desc} ({wait_ms}ms dwell)")

                        if action == "click" and selector:
                            try:
                                page.wait_for_selector(selector, timeout=7000)
                                el = page.query_selector(selector)
                                if el:
                                    try:
                                        el.scroll_into_view_if_needed(timeout=3000)
                                    except Exception:
                                        pass
                                    box = el.bounding_box()
                                    if box:
                                        cx = box["x"] + box["width"] / 2
                                        cy = box["y"] + box["height"] / 2
                                        page.mouse.move(cx, cy, steps=12)
                                        page.wait_for_timeout(350)
                                        page.mouse.click(cx, cy)
                                    else:
                                        el.click()
                            except Exception as ce:
                                logger.debug(f"Selector click notice ({selector}): {ce}")
                            page.wait_for_timeout(wait_ms)

                        elif action == "hover" and selector:
                            try:
                                page.wait_for_selector(selector, timeout=5000)
                                el = page.query_selector(selector)
                                if el:
                                    try:
                                        el.scroll_into_view_if_needed(timeout=2000)
                                    except Exception:
                                        pass
                                    box = el.bounding_box()
                                    if box:
                                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=10)
                            except Exception:
                                pass
                            page.wait_for_timeout(wait_ms)

                        elif action == "slider" and selector:
                            try:
                                target_val = step.get("value", "35")
                                page.wait_for_selector(selector, timeout=6000)
                                el = page.query_selector(selector)
                                if el:
                                    try:
                                        el.scroll_into_view_if_needed(timeout=2000)
                                    except Exception:
                                        pass
                                    box = el.bounding_box()
                                    if box:
                                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=12)
                                        page.wait_for_timeout(250)
                                    page.eval_on_selector(
                                        selector,
                                        f"(el) => {{ el.value = '{target_val}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); el.dispatchEvent(new Event('change', {{ bubbles: true }})); }}"
                                    )
                            except Exception as se:
                                logger.debug(f"Slider error ({selector}): {se}")
                            page.wait_for_timeout(wait_ms)

                        elif action == "select" and selector:
                            try:
                                opt_val = step.get("value")
                                page.wait_for_selector(selector, timeout=6000)
                                el = page.query_selector(selector)
                                if el:
                                    try:
                                        el.scroll_into_view_if_needed(timeout=2000)
                                    except Exception:
                                        pass
                                    box = el.bounding_box()
                                    if box:
                                        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=10)
                                        page.wait_for_timeout(250)
                                    page.select_option(selector, opt_val)
                            except Exception as se:
                                logger.debug(f"Select error ({selector}): {se}")
                            page.wait_for_timeout(wait_ms)

                        elif action == "scroll":
                            delta = step.get("delta_y", 350)
                            steps_count = 6
                            sub_delta = delta // steps_count
                            for _ in range(steps_count):
                                page.mouse.wheel(0, sub_delta)
                                page.wait_for_timeout(180)
                            page.wait_for_timeout(wait_ms)

                    logger.info(f"All {len(custom_interactions)} interactions completed. Total recording elapsed: {time.time() - start_time:.2f}s")

                else:
                    # 4. Multimodal Gemini Vision Director Mode
                    initial_screenshot = page.screenshot(type="jpeg", quality=85)
                    ai_steps = self._get_vision_tour_plan(initial_screenshot, project_name, custom_duration)

                    # 5. Execute Vision Tour Plan
                    if ai_steps:
                        logger.info(f"Executing AI Vision Director Tour ({len(ai_steps)} steps)...")
                        for step in ai_steps:
                            if time.time() - start_time >= (custom_duration - 4):
                                break
                            action = step.get("action", "hover")
                            desc = step.get("description", action)
                            x = min(1260, max(20, step.get("x", 640)))
                            y = min(700, max(20, step.get("y", 360)))
                            wait_ms = step.get("wait_ms", 2000)

                            logger.info(f"AI Vision Action: {desc} (action={action})")

                            if action in ("hover", "move"):
                                page.mouse.move(x, y, steps=10)
                                page.wait_for_timeout(wait_ms)
                            elif action == "click":
                                page.mouse.move(x, y, steps=10)
                                page.wait_for_timeout(350)
                                page.mouse.click(x, y)
                                page.wait_for_timeout(wait_ms)
                            elif action == "scroll":
                                delta = step.get("delta_y", 300)
                                for _ in range(3):
                                    page.mouse.wheel(0, delta // 3)
                                    page.wait_for_timeout(300)
                                page.wait_for_timeout(wait_ms)

                    # 6. Deep DOM Feature Explorer (Explores all remaining tabs, controls & charts)
                    self._explore_remaining_features(page, project_config, start_time, custom_duration)

            except Exception as e:
                logger.error(f"Recording interaction error: {e}")
            finally:
                page.close()
                context.close()
                browser.close()

        recorded_files = list(temp_record_dir.glob("*.webm")) + list(temp_record_dir.glob("*.mp4"))
        if not recorded_files:
            raise FileNotFoundError(f"No video recorded in {temp_record_dir}")

        raw_video = recorded_files[0]
        final_raw_path = self.raw_recordings_dir / f"{project_name}_raw{raw_video.suffix}"

        if final_raw_path.exists():
            final_raw_path.unlink()

        raw_video.rename(final_raw_path)
        try:
            temp_record_dir.rmdir()
        except Exception:
            pass

        logger.info(f"Vision-guided demo recording completed: {final_raw_path}")
        return final_raw_path

    def _explore_remaining_features(self, page, project_config: Dict[str, Any], start_time: float, total_sec: int):
        """
        Deep exploration fallback and companion:
        Scans all interactive buttons, tabs, dropdowns, and charts to guarantee
        that every main feature is showcased over the full duration budget.
        """
        def human_click(el):
            try:
                box = el.bounding_box()
                if box and el.is_visible():
                    cx = box["x"] + box["width"] / 2
                    cy = box["y"] + box["height"] / 2
                    page.mouse.move(cx, cy, steps=8)
                    page.wait_for_timeout(200)
                    el.click()
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                pass
            return False

        # Phase 1: Interactive buttons & views
        button_selectors = [
            "button:has-text('Mask')",
            "button:has-text('Overlay')",
            "button:has-text('Satellite')",
            "button:has-text('Predict')",
            "button:has-text('Analyze')",
            "button:has-text('Isometric')",
            "button[role='tab']",
            ".stTabs button",
            ".tab-btn",
            "button.btn-primary"
        ]

        for b_sel in button_selectors:
            if time.time() - start_time >= (total_sec - 6):
                break
            buttons = page.query_selector_all(b_sel)
            for btn in buttons[:2]:
                if btn.is_visible() and btn.is_enabled():
                    logger.info(f"Showcasing feature button: '{b_sel}'")
                    human_click(btn)
                    page.wait_for_timeout(1200)

        # Phase 2: Full Deep Page Scroll Tour (Show lower charts, metrics, and architecture)
        logger.info("Performing comprehensive visual scroll tour across charts & sections...")
        while time.time() - start_time < (total_sec - 8):
            page.mouse.wheel(0, 350)
            page.wait_for_timeout(1200)

        # Phase 3: Smooth return to hero section
        logger.info("Smoothly returning to top dashboard overview...")
        for _ in range(4):
            page.mouse.wheel(0, -350)
            page.wait_for_timeout(600)

        # Fill remaining duration
        elapsed = time.time() - start_time
        remaining = total_sec - elapsed
        if remaining > 0:
            page.wait_for_timeout(int(remaining * 1000))
        logger.info(f"Full feature exploration completed. Total elapsed: {time.time() - start_time:.2f}s")

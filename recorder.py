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
import math
import random
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
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

# Enhanced cinematic animated cursor overlay with expanding ripple wave feedback
CURSOR_INJECTION_SCRIPT = """
(function() {
    if (document.getElementById('playwright-demo-cursor')) return;
    
    // Primary cursor pointer with 3D radial depth and glowing aura
    const cursor = document.createElement('div');
    cursor.id = 'playwright-demo-cursor';
    cursor.style.cssText = `
        width: 20px;
        height: 20px;
        background: radial-gradient(circle at 35% 35%, #ff4b4b 0%, #d90429 100%);
        border: 2.5px solid #ffffff;
        border-radius: 50%;
        position: fixed;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: 2147483647;
        transition: transform 0.14s cubic-bezier(0.25, 1, 0.5, 1), background 0.18s ease, box-shadow 0.18s ease;
        box-shadow: 0 3px 12px rgba(0,0,0,0.4), 0 0 10px rgba(255, 75, 75, 0.5);
        transform: translate(-50%, -50%);
    `;
    
    // Expanding click ripple wave
    const ripple = document.createElement('div');
    ripple.id = 'playwright-demo-ripple';
    ripple.style.cssText = `
        width: 20px;
        height: 20px;
        border: 2px solid #10b981;
        border-radius: 50%;
        position: fixed;
        top: 0;
        left: 0;
        pointer-events: none;
        z-index: 2147483646;
        opacity: 0;
        transform: translate(-50%, -50%) scale(1);
        transition: transform 0.45s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.45s ease-out;
    `;
    
    document.documentElement.appendChild(cursor);
    document.documentElement.appendChild(ripple);

    window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
        ripple.style.left = e.clientX + 'px';
        ripple.style.top = e.clientY + 'px';
    }, { passive: true });

    window.addEventListener('mousedown', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.5)';
        cursor.style.background = 'radial-gradient(circle at 35% 35%, #34d399 0%, #059669 100%)';
        cursor.style.boxShadow = '0 0 16px rgba(16, 185, 129, 0.85)';
        
        // Trigger ripple pulse
        ripple.style.transition = 'none';
        ripple.style.transform = 'translate(-50%, -50%) scale(1)';
        ripple.style.opacity = '0.9';
        setTimeout(() => {
            ripple.style.transition = 'transform 0.45s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.45s ease-out';
            ripple.style.transform = 'translate(-50%, -50%) scale(2.8)';
            ripple.style.opacity = '0';
        }, 15);
    }, { passive: true });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.0)';
        cursor.style.background = 'radial-gradient(circle at 35% 35%, #ff4b4b 0%, #d90429 100%)';
        cursor.style.boxShadow = '0 3px 12px rgba(0,0,0,0.4), 0 0 10px rgba(255, 75, 75, 0.5)';
    }, { passive: true });
})();
"""


def generate_bezier_trajectory(start: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
    """
    Computes a natural, human-like Cubic Bézier trajectory between start and end coordinates.
    Includes perpendicular curvature arcs and sinusoidal ease-in-out velocity profiles.
    """
    x0, y0 = start
    x3, y3 = end
    dist = math.hypot(x3 - x0, y3 - y0)
    
    if dist < 6.0:
        return [(round(x3, 1), round(y3, 1))]
    
    # Calculate perpendicular direction for the arc
    perp_dx = -(y3 - y0) / (dist + 1e-6)
    perp_dy = (x3 - x0) / (dist + 1e-6)
    
    # Curve factor proportional to distance (capped for realistic reach)
    curve_factor = min(110.0, max(22.0, dist * 0.22))
    
    # Determine side of arc deterministically to avoid erratic flips
    side = 1.0 if (int(x0 * 10 + y0 * 10)) % 2 == 0 else -1.0
    dev1 = side * curve_factor * 0.70
    dev2 = side * curve_factor * 0.35
    
    # Control point 1 (1/3 mark + perpendicular offset)
    x1 = x0 + (x3 - x0) * 0.33 + perp_dx * dev1
    y1 = y0 + (y3 - y0) * 0.33 + perp_dy * dev1
    
    # Control point 2 (2/3 mark + subtle settling offset)
    x2 = x0 + (x3 - x0) * 0.66 + perp_dx * dev2
    y2 = y0 + (y3 - y0) * 0.66 + perp_dy * dev2
    
    # Dynamic step count scaled to travel distance (~60fps illusion)
    steps = max(14, min(42, int(dist / 16.0)))
    points = []
    
    for i in range(1, steps + 1):
        t_linear = i / float(steps)
        # Cosine ease-in-out easing (slow start, fast mid-flight, gentle settling)
        t = 0.5 * (1.0 - math.cos(math.pi * t_linear))
        
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t
        
        px = uuu * x0 + 3.0 * uu * t * x1 + 3.0 * u * tt * x2 + ttt * x3
        py = uuu * y0 + 3.0 * uu * t * y1 + 3.0 * u * tt * x2 + ttt * y3
        points.append((round(px, 1), round(py, 1)))
        
    return points


class ProjectRecorder:
    def __init__(self, raw_recordings_dir: Path):
        self.raw_recordings_dir = Path(raw_recordings_dir)
        self.raw_recordings_dir.mkdir(parents=True, exist_ok=True)
        self.gemini_client = None
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self._mouse_pos: Tuple[float, float] = (640.0, 360.0)

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and genai is not None:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
                logger.info(f"Gemini Vision Director initialized ({self.gemini_model}).")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Vision: {e}")

    def _smooth_mouse_move(self, page, target_x: float, target_y: float):
        """Moves cursor along a natural human-like Cubic Bézier curve with sinusoidal easing."""
        path = generate_bezier_trajectory(self._mouse_pos, (target_x, target_y))
        for (px, py) in path:
            page.mouse.move(px, py)
            page.wait_for_timeout(14)
        self._mouse_pos = (target_x, target_y)

    def _smooth_scroll(self, page, delta_y: int, wait_ms: int = 1500):
        """Executes silky smooth momentum scrolling with native window behavior & eased sub-steps."""
        try:
            page.evaluate(f"window.scrollBy({{ top: {delta_y}, left: 0, behavior: 'smooth' }});")
        except Exception:
            pass

        steps = 7
        for i in range(steps):
            weight = math.sin((i + 1) / float(steps) * math.pi)
            sub_delta = int((delta_y / float(steps)) * weight * 1.2)
            try:
                page.mouse.wheel(0, sub_delta)
            except Exception:
                pass
            page.wait_for_timeout(90)

        page.wait_for_timeout(wait_ms)

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

        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        server_log_path = logs_dir / f"server_{project_config.get('name', 'app')}.log"
        self._server_log_file = open(server_log_path, "w", encoding="utf-8", errors="replace")

        return subprocess.Popen(
            start_cmd,
            shell=True,
            cwd=str(project_folder),
            stdout=self._server_log_file,
            stderr=self._server_log_file,
            creationflags=creationflags
        )

    def stop_server(self, process: Optional[subprocess.Popen]):
        """Cleanly terminate server and all its child processes."""
        if hasattr(self, "_server_log_file") and self._server_log_file and not self._server_log_file.closed:
            try:
                self._server_log_file.flush()
                self._server_log_file.close()
            except Exception:
                pass

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
                args=[
                    "--start-maximized",
                    "--no-sandbox",
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                    "--use-gl=angle"
                ]
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
                                        cx = box["x"] + box["width"] / 2.0
                                        cy = box["y"] + box["height"] / 2.0
                                        self._smooth_mouse_move(page, cx, cy)
                                        page.wait_for_timeout(250)
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
                                        self._smooth_mouse_move(page, box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
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
                                        self._smooth_mouse_move(page, box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
                                        page.wait_for_timeout(200)
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
                                        self._smooth_mouse_move(page, box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
                                        page.wait_for_timeout(200)
                                    page.select_option(selector, opt_val)
                            except Exception as se:
                                logger.debug(f"Select error ({selector}): {se}")
                            page.wait_for_timeout(wait_ms)

                        elif action in ("type", "input") and selector:
                            try:
                                text_to_type = str(step.get("text", step.get("value", "")))
                                page.wait_for_selector(selector, timeout=6000)
                                el = page.query_selector(selector)
                                if el:
                                    try:
                                        el.scroll_into_view_if_needed(timeout=2000)
                                    except Exception:
                                        pass
                                    box = el.bounding_box()
                                    if box:
                                        self._smooth_mouse_move(page, box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
                                        page.wait_for_timeout(200)
                                    el.click()
                                    page.keyboard.press("Control+A")
                                    page.keyboard.press("Backspace")
                                    page.keyboard.type(text_to_type, delay=45)
                            except Exception as te:
                                logger.debug(f"Input/type error ({selector}): {te}")
                            page.wait_for_timeout(wait_ms)

                        elif action == "scroll":
                            delta = step.get("delta_y", 350)
                            self._smooth_scroll(page, delta, wait_ms=wait_ms)

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
                                self._smooth_mouse_move(page, float(x), float(y))
                                page.wait_for_timeout(wait_ms)
                            elif action == "click":
                                self._smooth_mouse_move(page, float(x), float(y))
                                page.wait_for_timeout(250)
                                page.mouse.click(x, y)
                                page.wait_for_timeout(wait_ms)
                            elif action == "scroll":
                                delta = step.get("delta_y", 300)
                                self._smooth_scroll(page, delta, wait_ms=wait_ms)

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
                    cx = box["x"] + box["width"] / 2.0
                    cy = box["y"] + box["height"] / 2.0
                    self._smooth_mouse_move(page, cx, cy)
                    page.wait_for_timeout(200)
                    el.click()
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                pass
            return False

        # Phase 0: Exhaustive Navigation Tab Traversal (Zero Overview-Only Trap)
        tab_selectors = [
            "button[data-tab]",
            "nav button",
            ".nav-links button",
            ".stTabs [data-baseweb='tab']",
            "[role='tab']",
            ".tab-btn"
        ]
        visited_tabs = set()
        for t_sel in tab_selectors:
            tab_elements = page.query_selector_all(t_sel)
            if tab_elements and len(tab_elements) > 1:
                logger.info(f"Discovered {len(tab_elements)} navigation tabs via '{t_sel}'. Traversing one by one...")
                for tab_el in tab_elements:
                    if time.time() - start_time >= (total_sec - 10):
                        break
                    tab_text = tab_el.inner_text().strip().replace('\n', ' ')
                    if tab_text and tab_text not in visited_tabs:
                        visited_tabs.add(tab_text)
                        logger.info(f"Navigating to tab: '{tab_text}'")
                        human_click(tab_el)
                        page.wait_for_timeout(3000)

                        # Trigger any action button on this newly revealed tab
                        action_btns = page.query_selector_all("button:has-text('Run'), button:has-text('Predict'), button:has-text('Simulate'), button:has-text('Generate'), button:has-text('Mask'), button:has-text('Overlay')")
                        for ab in action_btns[:2]:
                            if ab.is_visible() and ab.is_enabled():
                                human_click(ab)
                                page.wait_for_timeout(3000)

                        # If there are sliders, adjust one
                        sliders = page.query_selector_all("input[type='range']:visible")
                        if sliders:
                            sl = sliders[0]
                            box = sl.bounding_box()
                            if box:
                                self._smooth_mouse_move(page, box["x"] + box["width"] * 0.7, box["y"] + box["height"] / 2.0)
                                page.mouse.click(box["x"] + box["width"] * 0.7, box["y"] + box["height"] / 2.0)
                                page.wait_for_timeout(2000)

                break

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
            self._smooth_scroll(page, 350, wait_ms=900)

        # Phase 3: Smooth return to hero section
        logger.info("Smoothly returning to top dashboard overview...")
        for _ in range(4):
            self._smooth_scroll(page, -350, wait_ms=400)

        # Fill remaining duration
        elapsed = time.time() - start_time
        remaining = total_sec - elapsed
        if remaining > 0:
            page.wait_for_timeout(int(remaining * 1000))
        logger.info(f"Full feature exploration completed. Total elapsed: {time.time() - start_time:.2f}s")

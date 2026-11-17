"""
Project Runner & Deep Screen Recorder
Supports both Localhost servers and Live Vercel / Cloud deployments.
Features an Autonomous UI Explorer with visual mouse cursor injection that discovers
and clicks through tabs, toggles, form controls, and charts for realistic showcase videos.
"""

import os
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

# Visual mouse cursor overlay injected into page so LinkedIn viewers see the cursor actions
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
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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

    def is_live_url(self, url: str) -> bool:
        """Check if URL points to an external cloud deployment (e.g. Vercel, Render) rather than local."""
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

    def record_session(
        self,
        project_config: Dict[str, Any],
        duration_sec: int = 18
    ) -> Path:
        """
        Records the screen while navigating through features, tabs, and interactive controls.
        Works seamlessly for both localhost and Vercel/live URLs.
        """
        url = project_config.get("live_url") or project_config.get("url", "http://localhost:8501")
        project_name = project_config.get("name", "project_demo")
        custom_duration = project_config.get("record_duration_seconds", duration_sec)

        temp_record_dir = self.raw_recordings_dir / f"tmp_{project_name}"
        temp_record_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Launching Deep Feature Screen Recording for '{project_name}' on {url}...")

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
                page.wait_for_timeout(2000)

                # 2. Inject visible animated cursor
                try:
                    page.evaluate(CURSOR_INJECTION_SCRIPT)
                except Exception:
                    pass

                # 3. Deep Autonomous Exploration Tour
                self._explore_all_features(page, project_config, custom_duration)

            except Exception as e:
                logger.error(f"Exploration error during recording: {e}")
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

        logger.info(f"Deep demo recording completed: {final_raw_path}")
        return final_raw_path

    def _explore_all_features(self, page, project_config: Dict[str, Any], total_sec: int):
        """
        Deep Autonomous Feature Explorer:
        - Scans and switches between all tabs/views
        - Interacts with forms, sliders, and inputs
        - Clicks action buttons ('Predict', 'Analyze', 'Generate')
        - Smoothly pans across visual charts and key performance metrics
        """
        start_time = time.time()
        logger.info(f"Starting Autonomous Feature Exploration ({total_sec}s target)...")

        # Smooth mouse move helper
        def human_move_and_click(element):
            try:
                box = element.bounding_box()
                if box and element.is_visible():
                    center_x = box["x"] + box["width"] / 2
                    center_y = box["y"] + box["height"] / 2
                    page.mouse.move(center_x, center_y, steps=8)
                    page.wait_for_timeout(250)
                    element.click()
                    page.wait_for_timeout(900)
                    return True
            except Exception:
                pass
            return False

        # Phase 1: Header & Dashboard Overview Scan
        page.mouse.move(640, 200, steps=5)
        page.wait_for_timeout(800)

        # Phase 2: Systematic Tab Exploration (Find and explore every view)
        tab_selectors = [
            "button[role='tab']",
            ".stTabs [data-baseweb='tab']",
            ".stTabs button",
            ".tab-btn",
            "nav a.nav-link",
            "[data-testid='stSidebarNav'] a",
            "ul.nav li a",
            ".tabs button"
        ]

        found_tabs = []
        for sel in tab_selectors:
            tabs = page.query_selector_all(sel)
            if len(tabs) > 1:
                found_tabs = tabs
                logger.info(f"Found {len(tabs)} tabs/views using selector '{sel}'.")
                break

        if found_tabs:
            # Click each tab sequentially to showcase every section
            for idx, tab in enumerate(found_tabs):
                if time.time() - start_time > (total_sec - 5):
                    break
                logger.info(f"Exploring View/Tab {idx+1}/{len(found_tabs)}...")
                human_move_and_click(tab)

                # Scroll slightly to show content in this tab
                page.mouse.wheel(0, 200)
                page.wait_for_timeout(700)
                page.mouse.wheel(0, -200)
                page.wait_for_timeout(600)

            # Switch back to the primary interactive tab/view
            human_move_and_click(found_tabs[0])

        # Phase 3: Form Controls & Inputs (Adjust parameters/features)
        try:
            # Number inputs or text inputs
            inputs = page.query_selector_all("input[type='number'], input[type='text']")
            for inp in inputs[:2]:
                if inp.is_visible() and inp.is_enabled():
                    human_move_and_click(inp)
                    page.keyboard.press("ArrowUp")
                    page.wait_for_timeout(300)

            # Dropdown selects
            selects = page.query_selector_all("select")
            for sel in selects[:1]:
                if sel.is_visible():
                    human_move_and_click(sel)
                    page.keyboard.press("ArrowDown")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(400)
        except Exception as e:
            logger.debug(f"Input interaction skip: {e}")

        # Phase 4: Action / Execution Trigger (Predict / Calculate / Run)
        action_button_selectors = [
            "#predictBtn",
            "button:has-text('Predict')",
            "button:has-text('Run Churn Prediction')",
            "button:has-text('Analyze')",
            "button:has-text('Generate')",
            "button:has-text('Calculate')",
            "button:has-text('Submit')",
            "button.btn-primary",
            "button.primary"
        ]

        action_clicked = False
        for btn_sel in action_button_selectors:
            btn = page.query_selector(btn_sel)
            if btn and btn.is_visible() and btn.is_enabled():
                logger.info(f"Triggering primary action button: '{btn_sel}'")
                human_move_and_click(btn)
                action_clicked = True
                page.wait_for_timeout(1500)
                break

        # Phase 5: Result & Analytics Showcase (Smooth scroll down and up)
        logger.info("Showcasing results and interactive charts...")
        for _ in range(3):
            page.mouse.wheel(0, 250)
            page.wait_for_timeout(600)

        for _ in range(3):
            page.mouse.wheel(0, -250)
            page.wait_for_timeout(500)

        # Dwell remaining time if any
        elapsed = time.time() - start_time
        remaining = total_sec - elapsed
        if remaining > 0:
            page.wait_for_timeout(int(remaining * 1000))
        logger.info("Autonomous exploration completed.")

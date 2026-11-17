"""
Project Runner & Screen Recorder
Starts a local project server, interacts via Playwright with video recording enabled,
and cleanly terminates the server process.
"""

import os
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import urllib.request
import urllib.error

import psutil
from playwright.sync_api import sync_playwright

logger = logging.getLogger("Pipeline.Recorder")


class ProjectRecorder:
    def __init__(self, raw_recordings_dir: Path):
        self.raw_recordings_dir = Path(raw_recordings_dir)
        self.raw_recordings_dir.mkdir(parents=True, exist_ok=True)

    def _is_server_responsive(self, url: str) -> bool:
        """Check if the HTTP server is responsive."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                return response.status in (200, 301, 302, 404, 403)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.error):
            return False

    def wait_for_server(self, url: str, timeout_sec: int = 30) -> bool:
        """Poll the target URL until it becomes available or timeout expires."""
        logger.info(f"Waiting for server at {url} (up to {timeout_sec}s)...")
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if self._is_server_responsive(url):
                logger.info(f"Server is up and responsive at {url}!")
                return True
            time.sleep(1.0)
        logger.warning(f"Timed out waiting for server at {url} after {timeout_sec}s.")
        return False

    def start_server(self, project_config: Dict[str, Any]) -> subprocess.Popen:
        """Start the local application server subprocess cleanly."""
        start_cmd = project_config.get("start_command")
        project_folder = Path(project_config.get("folder_path", "."))

        if not start_cmd:
            raise ValueError(f"No start_command defined for project '{project_config.get('name')}'")

        if not project_folder.exists():
            raise FileNotFoundError(f"Project folder not found: {project_folder}")

        logger.info(f"Starting server in '{project_folder}': `{start_cmd}`")

        # Start process with shell=True for complex commands (e.g. streamlit run app.py)
        # On Windows, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP helps process tree control
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            start_cmd,
            shell=True,
            cwd=str(project_folder),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags
        )
        return process

    def stop_server(self, process: subprocess.Popen):
        """Cleanly kill the server process and all its child processes."""
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
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Give children a brief moment to exit gracefully
            _, still_alive = psutil.wait_procs(children, timeout=3)
            for child in still_alive:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Terminate parent
            try:
                parent.terminate()
                parent.wait(timeout=3)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    parent.kill()
                except psutil.NoSuchProcess:
                    pass

            logger.info(f"Server process {pid} and its children stopped.")
        except psutil.NoSuchProcess:
            logger.info(f"Process {pid} already stopped.")
        except Exception as e:
            logger.warning(f"Error terminating process {pid}: {e}")

    def record_session(
        self,
        project_config: Dict[str, Any],
        duration_sec: int = 15
    ) -> Path:
        """
        Record a Playwright browser session while performing realistic interactions.
        Returns the path to the saved raw video file (.webm or .mp4).
        """
        url = project_config.get("url", "http://localhost:8501")
        project_name = project_config.get("name", "project_demo")
        custom_duration = project_config.get("record_duration_seconds", duration_sec)

        temp_record_dir = self.raw_recordings_dir / f"tmp_{project_name}"
        temp_record_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Launching Playwright recording for '{project_name}' on {url}...")

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

                # 2. Automated interactions to showcase features
                self._perform_automated_interactions(page, project_config, custom_duration)

            except Exception as e:
                logger.error(f"Interaction error during recording: {e}")
            finally:
                # Video is only written after page and context are properly closed
                page.close()
                video_obj = page.video
                context.close()
                browser.close()

        # Locate the recorded video file in temp folder
        recorded_files = list(temp_record_dir.glob("*.webm")) + list(temp_record_dir.glob("*.mp4"))
        if not recorded_files:
            raise FileNotFoundError(f"Playwright did not output a video file in {temp_record_dir}")

        raw_video = recorded_files[0]
        final_raw_path = self.raw_recordings_dir / f"{project_name}_raw{raw_video.suffix}"

        if final_raw_path.exists():
            final_raw_path.unlink()

        raw_video.rename(final_raw_path)

        # Cleanup temp directory
        try:
            temp_record_dir.rmdir()
        except Exception:
            pass

        logger.info(f"Raw video recorded successfully: {final_raw_path}")
        return final_raw_path

    def _perform_automated_interactions(self, page, project_config: Dict[str, Any], total_sec: int):
        """Perform smooth scrolling, button clicks, and tab switching."""
        start_time = time.time()
        logger.info(f"Starting automated UI interactions ({total_sec}s budget)...")

        # Check for user-defined interaction steps
        custom_steps = project_config.get("interactions", [])
        if custom_steps:
            for step in custom_steps:
                action = step.get("action")
                selector = step.get("selector")
                wait_time = step.get("wait_ms", 1000)

                if action == "click" and selector:
                    try:
                        page.wait_for_selector(selector, timeout=3000)
                        page.click(selector)
                        logger.info(f"Clicked custom selector: {selector}")
                    except Exception:
                        pass
                elif action == "scroll":
                    delta = step.get("delta_y", 300)
                    page.mouse.wheel(0, delta)
                page.wait_for_timeout(wait_time)
            return

        # Default intelligent demonstration flow:
        # Phase 1: Initial look & Smooth scroll down
        page.wait_for_timeout(1500)
        for _ in range(3):
            page.mouse.wheel(0, 300)
            page.wait_for_timeout(800)

        # Phase 2: Click interactive tabs or primary buttons if available
        try:
            # Common UI framework buttons/tabs (Streamlit, Gradio, Bootstrap, Tailwind)
            interactive_selectors = [
                "button[data-baseweb='tab']",
                ".stTabs button",
                "button.primary",
                "button:has-text('Predict')",
                "button:has-text('Run')",
                "button:has-text('Analyze')",
                "button:has-text('Generate')",
                "button:has-text('Submit')",
                "button"
            ]
            for sel in interactive_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    for el in elements[:2]:
                        if el.is_visible() and el.is_enabled():
                            el.hover()
                            page.wait_for_timeout(400)
                            el.click()
                            page.wait_for_timeout(1200)
                            break
                    break
        except Exception as e:
            logger.debug(f"Default interaction skip: {e}")

        # Phase 3: Smooth scroll back up to show results / charts
        for _ in range(3):
            page.mouse.wheel(0, -300)
            page.wait_for_timeout(700)

        # Fill remaining duration
        elapsed = time.time() - start_time
        remaining = total_sec - elapsed
        if remaining > 0:
            page.wait_for_timeout(int(remaining * 1000))

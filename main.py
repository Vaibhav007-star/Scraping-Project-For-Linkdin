"""
Main Pipeline Orchestrator
Iterates through projects in projects_config.json, manages recording,
editing, AI copy generation, and safe publishing with error handling.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import argparse
from datetime import datetime

import config
from recorder import ProjectRecorder
from editor import VideoEditor
from copywriter import LinkedInCopywriter
from publisher import LinkedInPublisher


def setup_logger():
    """Configure structured logging for both terminal and file."""
    log_file = config.LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger, log_file


def load_projects_config(config_path: Path) -> List[Dict[str, Any]]:
    """Load and validate the projects configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "projects" in data:
        return data["projects"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Invalid format in projects_config.json: Expected list or {'projects': [...]}")


def process_single_project(
    project: Dict[str, Any],
    recorder: ProjectRecorder,
    editor: VideoEditor,
    copywriter: LinkedInCopywriter,
    publisher: LinkedInPublisher,
    logger: logging.Logger
) -> Dict[str, Any]:
    """Execute the full 4-stage pipeline for a single project with clean rollback/teardown."""
    project_name = project.get("name", "unnamed_project")
    project_title = project.get("title", project_name)

    logger.info("=" * 70)
    logger.info(f"Starting pipeline for: '{project_title}' ({project_name})")
    logger.info("=" * 70)

    server_process = None
    raw_video_path = None
    final_video_path = None

    try:
        # Stage 1: Spin up local server (if needed) & Record Screen
        url = project.get("live_url") or project.get("vercel_url") or project.get("url", "http://localhost:8501")
        if recorder.is_live_url(url):
            logger.info(f"[1/4] Project has a live cloud/Vercel URL: {url}. Recording directly without local server.")
        else:
            logger.info("[1/4] Launching local project server...")
            server_process = recorder.start_server(project)

        timeout = project.get("wait_timeout_seconds", 30)
        server_ready = recorder.wait_for_server(url, timeout_sec=timeout)
        if not server_ready:
            raise TimeoutError(f"Server at {url} failed to become responsive within {timeout} seconds.")

        logger.info("[1/4] Capturing automated Playwright recording...")
        raw_video_path = recorder.record_session(project)

    finally:
        # Always terminate the server process tree cleanly before moving to editing
        if server_process is not None:
            logger.info("[1/4] Cleaning up server process...")
            recorder.stop_server(server_process)

    # Stage 2: Video Editing (Trim initial 2s + 1.25x speed + H.264 MP4 export)
    logger.info("[2/4] Editing recording (Trimming blank load + 1.25x speedup)...")
    trim_sec = project.get("trim_start_sec", config.DEFAULT_TRIM_START_SEC)
    speed_factor = project.get("speed_factor", config.DEFAULT_SPEED_FACTOR)

    final_video_path = editor.process_video(
        raw_video_path=raw_video_path,
        output_filename=f"{project_name}_linkedin.mp4",
        trim_start_sec=trim_sec,
        speed_factor=speed_factor,
        project_config=project
    )

    # Stage 3: Humanized Copywriting via Google Gemini
    logger.info("[3/4] Generating humanized post copy via Gemini AI...")
    post_text = copywriter.generate_post(project)

    # Stage 4: Ban-Safe Publishing or Staging
    logger.info("[4/4] Staging / Publishing to LinkedIn...")
    result = publisher.publish_or_stage(
        project_config=project,
        video_path=final_video_path,
        post_text=post_text
    )

    logger.info(f"Successfully processed '{project_name}'. Status: {result.get('status')}")
    return {
        "project": project_name,
        "title": project_title,
        "status": "SUCCESS",
        "action": result.get("status"),
        "video": str(final_video_path),
        "details": result
    }


def main():
    parser = argparse.ArgumentParser(description="Automated LinkedIn Showcase Pipeline for AI & Data Science Projects")
    parser.add_argument(
        "--config",
        type=str,
        default="projects_config.json",
        help="Path to projects configuration JSON file (default: projects_config.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Enforce DRY_RUN review mode (saves to ready_to_post/ without calling LinkedIn API)"
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Specify a single project name to process instead of all 20"
    )

    args = parser.parse_args()
    logger, log_file = setup_logger()

    logger.info("=" * 70)
    logger.info("  LINKEDIN DATA SCIENCE & AI PROJECT AUTOMATION PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Log file: {log_file}")

    # Determine dry run status (CLI argument overrides config/.env)
    dry_run = config.DRY_RUN if args.dry_run is None else args.dry_run
    logger.info(f"Mode: {'DRY RUN (Review Mode: staging in ready_to_post/)' if dry_run else 'LIVE PUBLISHING (LinkedIn REST API)'}")

    # Load project configurations
    config_file = config.BASE_DIR / args.config
    try:
        projects = load_projects_config(config_file)
        logger.info(f"Loaded {len(projects)} project configuration(s) from {config_file.name}.")
    except Exception as e:
        logger.critical(f"Failed to load project configurations: {e}")
        sys.exit(1)

    # Filter for single project if requested
    if args.project:
        projects = [p for p in projects if p.get("name") == args.project]
        if not projects:
            logger.error(f"Project '{args.project}' not found in {config_file.name}.")
            sys.exit(1)
        logger.info(f"Filtered execution for single project: '{args.project}'")

    # Initialize modular components
    recorder = ProjectRecorder(raw_recordings_dir=config.RECORDINGS_DIR)
    editor = VideoEditor(output_dir=config.OUTPUT_DIR)
    copywriter = LinkedInCopywriter(
        api_key=config.GEMINI_API_KEY,
        model=config.GEMINI_MODEL
    )
    publisher = LinkedInPublisher(
        access_token=config.LINKEDIN_ACCESS_TOKEN,
        author_urn=config.LINKEDIN_AUTHOR_URN,
        dry_run=dry_run,
        ready_to_post_dir=config.READY_TO_POST_DIR
    )

    # Process all projects with fault tolerance
    results = []
    for index, project in enumerate(projects, start=1):
        p_name = project.get("name", f"project_{index}")
        logger.info(f"\nProcessing project {index}/{len(projects)}: {p_name}...")

        try:
            res = process_single_project(project, recorder, editor, copywriter, publisher, logger)
            results.append(res)
        except Exception as e:
            logger.error(f"FAILED processing project '{p_name}': {e}", exc_info=True)
            results.append({
                "project": p_name,
                "title": project.get("title", p_name),
                "status": "FAILED",
                "error": str(e)
            })

    # Summary report
    logger.info("\n" + "=" * 70)
    logger.info(" PIPELINE BATCH EXECUTION SUMMARY")
    logger.info("=" * 70)

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_count = sum(1 for r in results if r["status"] == "FAILED")

    logger.info(f"Total Projects Processed: {len(results)}")
    logger.info(f"Successful:              {success_count}")
    logger.info(f"Failed:                  {failed_count}")
    logger.info("-" * 70)

    for r in results:
        status_icon = "[OK]" if r["status"] == "SUCCESS" else "[FAIL]"
        logger.info(f"{status_icon} {r['project']}: {r.get('action', r.get('error'))}")

    if dry_run and success_count > 0:
        logger.info("\n" + "*" * 70)
        logger.info("DRY RUN COMPLETE:")
        logger.info(f"Review your final videos and post text in: {config.READY_TO_POST_DIR.resolve()}")
        logger.info("When ready to publish, set DRY_RUN=False in .env and run again.")
        logger.info("*" * 70)


if __name__ == "__main__":
    main()

"""
Global Configuration & Environment Management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the pipeline
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env")

# Directories
RECORDINGS_DIR = BASE_DIR / "recordings"
OUTPUT_DIR = BASE_DIR / "output"
READY_TO_POST_DIR = BASE_DIR / "ready_to_post"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [RECORDINGS_DIR, OUTPUT_DIR, READY_TO_POST_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Google Gemini API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# LinkedIn API Settings
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_AUTHOR_URN = os.getenv("LINKEDIN_AUTHOR_URN", "")  # e.g., "urn:li:person:XXXXX" or "urn:li:organization:XXXXX"

# Dry Run Mode: if True, do not call LinkedIn upload/post APIs; save files to ready_to_post/
DRY_RUN = os.getenv("DRY_RUN", "True").strip().lower() in ("true", "1", "yes")

# Default Video Processing Settings
DEFAULT_TRIM_START_SEC = float(os.getenv("TRIM_START_SEC", "2.0"))
DEFAULT_SPEED_FACTOR = float(os.getenv("SPEED_FACTOR", "1.18"))
DEFAULT_RECORD_DURATION_SEC = int(os.getenv("RECORD_DURATION_SEC", "40"))

# LinkedIn AI & Data Science Showcase Pipeline

A modular, 100% free-to-run Python automation pipeline that records, edits, writes humanized copy for, and publishes your Data Science and AI projects to LinkedIn without risking account bans.

---

## Architecture & Workflow

```text
+------------------------+      +-------------------------+      +---------------------------+
| 1. Project Runner &   | ---> | 2. Video Editor         | ---> | 3. Gemini Copywriter      |
|    Playwright Recorder |      |    (MoviePy H.264)      |      |    (google-genai SDK)     |
|    - Subprocess launch |      |    - Trim blank load    |      |    - No AI buzzwords      |
|    - Realistic UI tour |      |    - 1.25x pacing boost |      |    - Practitioner tone    |
|    - Clean process kill|      |    - yuv420p MP4 format |      |    - DS/AI Hashtags       |
+------------------------+      +-------------------------+      +---------------------------+
                                                                               |
                                                                               v
                                                                 +---------------------------+
                                                                 | 4. Ban-Safe Publisher     |
                                                                 |    (Official REST API)    |
                                                                 |    - DRY_RUN Review Mode  |
                                                                 |    - 3-Step Video Upload  |
                                                                 |    - Zero Browser Scraping|
                                                                 +---------------------------+
```

---

## Folder Structure

```text
Linkdin Pipline/
|-- .env                          # Local environment secrets (ignored by git)
|-- .env.example                  # Template configuration file
|-- .gitignore                    # Prevents secret leaks, venv, and large videos from git
|-- config.py                     # Central configuration loader
|-- recorder.py                   # Playwright recording & server process supervisor
|-- editor.py                     # MoviePy automated video trimming & 1.25x speedup
|-- copywriter.py                 # Google Gemini (google-genai) prompt & post generator
|-- publisher.py                  # Official LinkedIn REST API integration (Posts & Videos)
|-- main.py                       # Orchestrator script looping through projects_config.json
|-- projects_config.json          # Configuration array for your 20 Data Science/AI projects
|-- requirements.txt              # Pipeline dependencies (google-genai, playwright, moviepy)
|-- sample_projects/
|   `-- churn_dashboard/          # Built-in test project for immediate verification
|       |-- app.py                # Standalone interactive dashboard server
|       `-- README.md             # Project documentation for Gemini context
`-- ready_to_post/                # Output folder for DRY_RUN manual review
    `-- <project_name>/
        |-- demo.mp4              # Final 1.25x H.264 video
        |-- post.txt              # Generated LinkedIn post copy
        `-- metadata.json         # Timestamps, file size, and publication metrics
```

---

## Quick Start & Installation

### 1. Set Up Virtual Environment (Already Initialized)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

---

## Free API Credentials Guide

### 1. Google Gemini API Key (100% Free Tier)
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **"Get API key"** in the top left.
4. Click **"Create API key in new project"**.
5. Copy your API key and add it to `.env`:
   ```env
   GEMINI_API_KEY=your_copied_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```

### 2. LinkedIn REST API Access Token (100% Free & Ban-Safe)
> **Why REST API?** Logging into LinkedIn via Selenium or Playwright triggers bot detection checkpoints and risks permanent account suspension. Using the official LinkedIn REST API with developer tokens is 100% compliant and ban-safe.

1. Navigate to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Click **"Create App"**:
   - **App name**: e.g., `Portfolio Automation Engine`
   - **LinkedIn Page**: Link your personal or company page.
   - **App logo**: Upload any square icon.
3. In the **"Products"** tab of your app, request access to:
   - **Share on LinkedIn** (Provides `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (Provides `openid`, `profile`)
4. In the **"Auth"** tab, generate an OAuth 2.0 Access Token:
   - Under **OAuth 2.0 Tools**, click **"Create token"**.
   - Select scopes: `w_member_social`, `openid`, `profile`.
   - Authorize your app and copy the generated **Access Token**.
5. Retrieve your Member URN:
   - Run a quick curl or GET request to `https://api.linkedin.com/v2/userinfo` with header `Authorization: Bearer <ACCESS_TOKEN>`.
   - Your `sub` field is your person ID (e.g., `12345678`), making your URN: `urn:li:person:12345678`.
6. Add these to `.env`:
   ```env
   LINKEDIN_ACCESS_TOKEN=AQX...your_token...
   LINKEDIN_AUTHOR_URN=urn:li:person:12345678
   DRY_RUN=True
   ```

---

## Running the Pipeline

### 1. Test Run on the Built-In Sample Project (DRY_RUN Mode)
Run a test on the included Customer Churn Dashboard to record, edit, and generate copy:
```powershell
.\.venv\Scripts\python.exe main.py --project churn_prediction_platform
```
- Playwright starts the dashboard on `localhost:8501`.
- Captures automated interactions (scrolling, clicking prediction buttons).
- MoviePy trims the initial 2.0s blank load and speeds up playback by 1.25x.
- Gemini writes a natural post highlighting the business problem, solution, impact, and tech stack without buzzwords.
- The output is staged in `ready_to_post/churn_prediction_platform/` for your inspection!

### 2. Run All 20 Projects in Review Mode
```powershell
.\.venv\Scripts\python.exe main.py --dry-run
```

### 3. Go Live to LinkedIn
Once you have reviewed the generated videos and posts in `ready_to_post/`:
1. Change `DRY_RUN=False` in `.env`.
2. Run the orchestrator:
   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```
   The pipeline will automatically upload each `.mp4` video binary chunk to LinkedIn and publish the post directly to your feed.

---

## Configuring Your 20 Projects

Edit `projects_config.json` with the local paths and start commands for your projects:
```json
{
  "name": "fraud_detection_engine",
  "title": "Real-Time Credit Card Fraud Detection Engine",
  "folder_path": "projects/fraud_detection",
  "start_command": "uvicorn main:app --port 8000",
  "url": "http://localhost:8000/docs",
  "port": 8000,
  "wait_timeout_seconds": 25,
  "record_duration_seconds": 15,
  "main_script_path": "main.py",
  "readme_path": "README.md"
}
```

The pipeline handles:
- **Streamlit**: `streamlit run app.py --server.port 8501 --server.headless true`
- **FastAPI / Uvicorn**: `uvicorn main:app --port 8000`
- **Flask**: `python app.py`
- **Gradio**: `python app.py`

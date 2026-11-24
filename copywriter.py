"""
Humanized LinkedIn Copy & Hashtag Generator
Analyzes project README and main source code, then generates an authentic,
first-person Data Scientist LinkedIn post via Google Gemini API (google-genai SDK).
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("Pipeline.Copywriter")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# Banned AI Buzzwords list
BANNED_BUZZWORDS = [
    "delve", "delving",
    "testament",
    "game-changer", "game changer",
    "realm",
    "revolutionize", "revolutionizing", "revolutionary",
    "tapestry",
    "in an era where",
    "dive deep",
    "harness", "harnessing",
    "beacon",
    "pleased to announce",
    "thrilled to share",
    "fosters", "synergy"
]


class LinkedInCopywriter:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.client = None

        if self.api_key and genai is not None:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Gemini Client with model '{self.model}'.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}")
        else:
            logger.info("No Gemini API key provided. Offline fallback copy generator will be used if needed.")

    def _read_project_context(self, project_config: Dict[str, Any]) -> Dict[str, str]:
        """Extract README, code, or live website text for project context."""
        has_local_folder = "folder_path" in project_config and project_config["folder_path"]
        live_url = project_config.get("live_url") or (project_config.get("url") if "http" in project_config.get("url", "") and "localhost" not in project_config.get("url", "") else None)

        readme_text = ""
        script_text = ""

        # 1. If local folder is configured, read local files
        if has_local_folder:
            project_folder = Path(project_config["folder_path"])
            readme_path = project_config.get("readme_path", "README.md")
            script_path = project_config.get("main_script_path", "app.py")

            full_readme = project_folder / readme_path
            full_script = project_folder / script_path

            if full_readme.exists() and full_readme.is_file():
                try:
                    readme_text = full_readme.read_text(encoding="utf-8", errors="ignore")[:4000]
                except Exception as e:
                    logger.warning(f"Error reading README at {full_readme}: {e}")

            if full_script.exists() and full_script.is_file():
                try:
                    script_text = full_script.read_text(encoding="utf-8", errors="ignore")[:3000]
                except Exception as e:
                    logger.warning(f"Error reading script at {full_script}: {e}")

        # 2. If live URL is present (e.g. Vercel deployment), extract rich text from live site
        if live_url:
            try:
                import requests
                resp = requests.get(live_url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    raw_html = resp.text
                    clean_text = re.sub(r"<(script|style|head|noscript)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
                    clean_text = re.sub(r"<[^>]+>", " ", clean_text)
                    clean_text = " ".join(clean_text.split())
                    live_summary = f"Live Project Content from {live_url}:\n{clean_text[:4000]}"
                    if readme_text:
                        readme_text += f"\n\n{live_summary}"
                    else:
                        readme_text = live_summary
                    logger.info(f"Extracted {len(clean_text[:4000])} chars of context from live URL: {live_url}")
            except Exception as e:
                logger.warning(f"Could not fetch live context from {live_url}: {e}")

        # 3. Resolve GitHub Repository URL (from config or git remote)
        github_url = project_config.get("github_url", "")
        if not github_url and has_local_folder:
            try:
                import subprocess
                res = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(Path(project_config["folder_path"])),
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if res.returncode == 0 and res.stdout.strip():
                    url = res.stdout.strip()
                    if url.endswith(".git"):
                        url = url[:-4]
                    if url.startswith("git@github.com:"):
                        url = "https://github.com/" + url.split(":", 1)[1]
                    github_url = url
            except Exception:
                pass

        return {
            "title": project_config.get("title", project_config.get("name", "Data Science Project")),
            "readme": readme_text,
            "script": script_text,
            "github_url": github_url,
            "live_url": live_url or ""
        }

    def _clean_and_validate_copy(
        self,
        raw_text: str,
        github_url: str = "",
        live_url: str = "",
        tech_tags: str = ""
    ) -> str:
        """Sanitize output, remove code fences, enforce repo links, and ensure valid hashtags."""
        # Strip code fences if model wrapped in markdown
        cleaned = re.sub(r"^```(?:markdown|text)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

        # Check for banned buzzwords and warn if present
        found_buzzwords = [word for word in BANNED_BUZZWORDS if re.search(rf"\b{re.escape(word)}\b", cleaned, re.IGNORECASE)]
        if found_buzzwords:
            logger.warning(f"Warning: Output contained flagged AI buzzwords: {found_buzzwords}")
            for bw in found_buzzwords:
                pattern = re.compile(rf"\b{re.escape(bw)}\b", re.IGNORECASE)
                if "game-changer" in bw:
                    cleaned = pattern.sub("significant milestone", cleaned)
                elif "delve" in bw:
                    cleaned = pattern.sub("examine", cleaned)
                elif "realm" in bw:
                    cleaned = pattern.sub("domain", cleaned)
                elif "testament" in bw:
                    cleaned = pattern.sub("proof", cleaned)

        # MANDATORY CHECK 1: Ensure GitHub repository link is present
        if github_url and github_url not in cleaned:
            logger.info(f"Injecting mandatory GitHub repository link: {github_url}")
            links_block = f"\n\nProject Links:\n- GitHub Repository: {github_url}"
            if live_url and live_url not in cleaned:
                links_block += f"\n- Live Platform: {live_url}"

            # Insert before hashtags if present, else append
            hashtag_match = re.search(r"(?:^|\n)(#[A-Za-z0-9_]+(?:\s+#[A-Za-z0-9_]+)*\s*)$", cleaned)
            if hashtag_match:
                start_pos = hashtag_match.start()
                cleaned = cleaned[:start_pos].rstrip() + links_block + "\n\n" + cleaned[start_pos:].lstrip()
            else:
                cleaned += links_block

        # MANDATORY CHECK 2: Ensure hashtags are present (minimum 4)
        hashtags = re.findall(r"#[A-Za-z0-9_]+", cleaned)
        if len(hashtags) < 4:
            logger.info("Fewer than 4 hashtags detected. Appending standard domain hashtags...")
            default_tags = "#ArtificialIntelligence #MachineLearning #SoftwareEngineering #Python #OpenSource"
            cleaned = cleaned.rstrip() + "\n\n" + default_tags

        return cleaned.strip()

    def generate_post(self, project_config: Dict[str, Any]) -> str:
        """
        Generate a compelling, humanized LinkedIn post following strict rules:
        Hook -> Business Problem -> Technical Solution -> Impact -> Tech Stack -> Project Links -> Demo Callout -> Hashtags.
        """
        context = self._read_project_context(project_config)
        project_name = context["title"]
        github_url = context["github_url"]
        live_url = context["live_url"]

        if not self.client:
            logger.warning(f"Gemini API key not configured. Generating standard authentic template for '{project_name}'.")
            return self._generate_fallback_copy(project_config, context)

        system_instruction = (
            "You are a Senior Data Scientist and Machine Learning Engineer. "
            "Write an engaging, authentic, first-person LinkedIn post showcasing a project you built. "
            "Strictly follow this structure:\n"
            "1. Hook: 1 punchy, results-oriented opening line (avoid cringe or clickbait).\n"
            "2. Business Problem: Briefly state the real-world operational or analytical bottleneck.\n"
            "3. Technical Solution: Highlight the architectural approach, model selection, or pipeline design.\n"
            "4. Impact & Results: Concrete quantitative or qualitative improvement.\n"
            "5. Tech Stack: Concise bullet list of tools and libraries used.\n"
            "6. Project Links: You MUST include the GitHub Repository link provided under 'Project Links:'.\n"
            "7. Demo Video Callout & Peer Question: Mention the attached demo video and ask an engaging technical question.\n"
            "8. Hashtags: Exactly 5 to 7 high-impact hashtags at the very bottom.\n\n"
            "STRICT RULES:\n"
            "- Tone: Natural, professional, practitioner voice. Do NOT sound like a marketer or ChatGPT.\n"
            "- BANNED WORDS: Never use 'delve', 'testament', 'game-changer', 'realm', 'revolutionize', "
            "'tapestry', 'beacon', 'unleash', 'in today's world', 'thrilled to announce'.\n"
            "- MANDATORY: You MUST explicitly include the GitHub Repository link in the post body.\n"
            "- MANDATORY: You MUST explicitly include 5 to 7 hashtags with '#' at the end.\n"
            "- Keep paragraphs short and readable on mobile."
        )

        user_prompt = f"""
Project Title: {project_name}

GitHub Repository: {github_url or 'https://github.com/Vaibhav007-star'}
Live Platform URL: {live_url or 'None'}

README excerpt:
{context['readme'] or 'No README provided. Infer from code.'}

Source code excerpt:
{context['script'] or 'No source code provided.'}

Write the LinkedIn post now following the exact required structure, ensuring the GitHub Repository link and hashtags are prominently included.
"""

        try:
            post_text = None
            models_to_try = [self.model, "gemini-3.1-flash-lite", "gemini-3.8-flash"]
            # Deduplicate while preserving order
            seen = set()
            unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            for model_name in unique_models:
                try:
                    logger.info(f"Calling Gemini API ({model_name}) for '{project_name}'...")
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[system_instruction, user_prompt]
                    )
                    if response and response.text:
                        post_text = self._clean_and_validate_copy(
                            response.text,
                            github_url=github_url,
                            live_url=live_url
                        )
                        logger.info(f"Generated copy for '{project_name}' ({len(post_text)} chars) using {model_name}.")
                        return post_text
                except Exception as me:
                    logger.warning(f"Model {model_name} error: {me}. Trying next model if available...")

            if not post_text:
                return self._generate_fallback_copy(project_config, context)

        except Exception as e:
            logger.error(f"Gemini API error: {e}. Using fallback template.")
            return self._generate_fallback_copy(project_config, context)

    def _generate_fallback_copy(self, project_config: Dict[str, Any], context: Dict[str, str]) -> str:
        """High-quality fallback template adhering strictly to prompt guidelines when API key is missing."""
        title = context["title"]
        github_url = context.get("github_url", "")
        links_section = f"Project Links:\n- GitHub Repository: {github_url}\n\n" if github_url else ""
        return (
            f"Most predictive models fail when moving from Jupyter notebooks to real-time production.\n\n"
            f"Here is how I built and deployed {title} to bridge that gap.\n\n"
            f"The Business Challenge:\n"
            f"Manual evaluation workflows created delays and inconsistent forecasting accuracy across incoming data streams.\n\n"
            f"The Technical Approach:\n"
            f"Built an end-to-end automated inference pipeline. Implemented feature validation, gradient boosted models, "
            f"and cached predictions behind an interactive monitoring interface for instant diagnostic inspection.\n\n"
            f"The Impact:\n"
            f"• Sub-second inference latency on new sample batches\n"
            f"• Reproducible data transformation and baseline metrics tracking\n"
            f"• Interactive visual dashboard for rapid stakeholder decision-making\n\n"
            f"Tech Stack:\n"
            f"• Python / Pandas / Scikit-Learn\n"
            f"• Streamlit / FastAPI\n"
            f"• Playwright / Automated Validation\n\n"
            f"{links_section}"
            f"The complete demonstration walkthrough with neural narration is attached below.\n\n"
            f"#DataScience #MachineLearning #ArtificialIntelligence #Python #MLOps #OpenSource"
        )

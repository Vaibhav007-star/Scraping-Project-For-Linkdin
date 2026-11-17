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
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
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
        """Extract README and main script contents for context."""
        project_folder = Path(project_config.get("folder_path", "."))
        readme_path = project_config.get("readme_path", "README.md")
        script_path = project_config.get("main_script_path", "app.py")

        full_readme = project_folder / readme_path
        full_script = project_folder / script_path

        readme_text = ""
        script_text = ""

        if full_readme.exists():
            try:
                readme_text = full_readme.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception as e:
                logger.warning(f"Error reading README at {full_readme}: {e}")

        if full_script.exists():
            try:
                script_text = full_script.read_text(encoding="utf-8", errors="ignore")[:3000]
            except Exception as e:
                logger.warning(f"Error reading script at {full_script}: {e}")

        return {
            "title": project_config.get("title", project_config.get("name", "Data Science Project")),
            "readme": readme_text,
            "script": script_text
        }

    def _clean_and_validate_copy(self, raw_text: str) -> str:
        """Sanitize output, remove code fences, and check for banned words."""
        # Strip code fences if model wrapped in markdown
        cleaned = re.sub(r"^```(?:markdown|text)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

        # Check for banned buzzwords and warn if present
        found_buzzwords = [word for word in BANNED_BUZZWORDS if re.search(rf"\b{re.escape(word)}\b", cleaned, re.IGNORECASE)]
        if found_buzzwords:
            logger.warning(f"Warning: Output contained flagged AI buzzwords: {found_buzzwords}")
            for bw in found_buzzwords:
                # Replace common buzzwords cleanly if found
                pattern = re.compile(rf"\b{re.escape(bw)}\b", re.IGNORECASE)
                if "game-changer" in bw:
                    cleaned = pattern.sub("significant milestone", cleaned)
                elif "delve" in bw:
                    cleaned = pattern.sub("examine", cleaned)
                elif "realm" in bw:
                    cleaned = pattern.sub("domain", cleaned)
                elif "testament" in bw:
                    cleaned = pattern.sub("proof", cleaned)

        return cleaned.strip()

    def generate_post(self, project_config: Dict[str, Any]) -> str:
        """
        Generate a compelling, humanized LinkedIn post following strict rules:
        Hook -> Business Problem -> Technical Solution -> Impact -> Tech Stack -> 4-5 Hashtags.
        """
        context = self._read_project_context(project_config)
        project_name = context["title"]

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
            "4. Impact & Results: Concrete quantitative or qualitative improvement (latency, accuracy, cost, or usability).\n"
            "5. Tech Stack: Concise bullet list of tools and libraries used.\n"
            "6. Hashtags: Exactly 4 to 5 relevant hashtags at the bottom.\n\n"
            "STRICT RULES:\n"
            "- Tone: Natural, professional, practitioner voice. Do NOT sound like a marketer or ChatGPT.\n"
            "- BANNED WORDS: Never use 'delve', 'testament', 'game-changer', 'realm', 'revolutionize', "
            "'tapestry', 'beacon', 'unleash', 'in today's world', 'thrilled to announce'.\n"
            "- Do NOT include generic motivational intros or generic sign-offs.\n"
            "- Keep paragraphs short and readable on mobile."
        )

        user_prompt = f"""
Project Title: {project_name}

README excerpt:
{context['readme'] or 'No README provided. Infer from code.'}

Source code excerpt:
{context['script'] or 'No source code provided.'}

Write the LinkedIn post now following the exact required structure.
"""

        try:
            logger.info(f"Calling Gemini API ({self.model}) for '{project_name}'...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=[system_instruction, user_prompt]
            )

            if response and response.text:
                post_text = self._clean_and_validate_copy(response.text)
                logger.info(f"Generated copy for '{project_name}' ({len(post_text)} chars).")
                return post_text
            else:
                logger.warning("Empty response from Gemini API, falling back to local copy.")
                return self._generate_fallback_copy(project_config, context)

        except Exception as e:
            logger.error(f"Gemini API error: {e}. Using fallback template.")
            return self._generate_fallback_copy(project_config, context)

    def _generate_fallback_copy(self, project_config: Dict[str, Any], context: Dict[str, str]) -> str:
        """High-quality fallback template adhering strictly to prompt guidelines when API key is missing."""
        title = context["title"]
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
            f"Check out the demo recording above!\n\n"
            f"#DataScience #MachineLearning #ArtificialIntelligence #Python #MLOps"
        )

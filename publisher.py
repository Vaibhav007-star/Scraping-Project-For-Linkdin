"""
Ban-Safe LinkedIn Publisher
Publishes video demonstrations and humanized copy using the official LinkedIn REST API
(Videos API & Posts API). Completely avoids browser scraping to protect account standing.
Includes DRY_RUN review mode to inspect assets locally before posting.
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import requests

logger = logging.getLogger("Pipeline.Publisher")


class LinkedInPublisher:
    def __init__(
        self,
        access_token: Optional[str] = None,
        author_urn: Optional[str] = None,
        dry_run: bool = True,
        ready_to_post_dir: Optional[Path] = None
    ):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.author_urn = author_urn or os.getenv("LINKEDIN_AUTHOR_URN", "")
        self.dry_run = dry_run
        self.ready_to_post_dir = Path(ready_to_post_dir or "ready_to_post")
        self.ready_to_post_dir.mkdir(parents=True, exist_ok=True)

        self.api_version = os.getenv("LINKEDIN_API_VERSION", "202611")
        self.base_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def publish_or_stage(
        self,
        project_config: Dict[str, Any],
        video_path: Path,
        post_text: str
    ) -> Dict[str, Any]:
        """
        Either stages the video and post into ready_to_post/ for human review (DRY_RUN=True),
        or publishes directly to LinkedIn using official REST APIs (DRY_RUN=False).
        """
        project_name = project_config.get("name", "project")
        video_path = Path(video_path)

        # Force DRY_RUN if credentials are not configured
        is_dry_run = self.dry_run or not self.access_token or not self.author_urn

        if is_dry_run:
            if not self.access_token or not self.author_urn:
                logger.info(
                    f"[{project_name}] Running in DRY_RUN mode (credentials not fully configured in .env)."
                )
            else:
                logger.info(f"[{project_name}] Running in DRY_RUN mode (review mode enabled).")

            return self._stage_for_review(project_config, video_path, post_text)
        else:
            logger.info(f"[{project_name}] DRY_RUN is False. Publishing directly to LinkedIn REST API...")
            return self._publish_to_linkedin(project_config, video_path, post_text)

    def _stage_for_review(
        self,
        project_config: Dict[str, Any],
        video_path: Path,
        post_text: str
    ) -> Dict[str, Any]:
        """Save video, text copy, and metadata to ready_to_post/<project_name>/ for manual inspection."""
        project_name = project_config.get("name", "project")
        stage_dir = self.ready_to_post_dir / project_name
        stage_dir.mkdir(parents=True, exist_ok=True)

        staged_video = stage_dir / f"{project_name}_demo.mp4"
        shutil.copy2(video_path, staged_video)

        post_file = stage_dir / "post.txt"
        post_file.write_text(post_text, encoding="utf-8")

        metadata = {
            "project_name": project_name,
            "project_title": project_config.get("title", project_name),
            "created_at": datetime.now().isoformat(),
            "video_path": str(staged_video),
            "video_size_mb": round(staged_video.stat().st_size / (1024 * 1024), 2),
            "text_length_chars": len(post_text),
            "status": "READY_FOR_REVIEW",
            "publish_instructions": "Review post.txt and demo.mp4. When satisfied, set DRY_RUN=False to publish."
        }

        meta_file = stage_dir / "metadata.json"
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        logger.info(f" staged assets in '{stage_dir}':")
        logger.info(f"   - Video: {staged_video.name} ({metadata['video_size_mb']} MB)")
        logger.info(f"   - Copy:  {post_file.name} ({len(post_text)} characters)")

        return {
            "status": "STAGED",
            "folder": str(stage_dir),
            "video": str(staged_video),
            "post_file": str(post_file),
            "metadata": metadata
        }

    def _publish_to_linkedin(
        self,
        project_config: Dict[str, Any],
        video_path: Path,
        post_text: str
    ) -> Dict[str, Any]:
        """
        Official 3-Step LinkedIn REST Video Posting:
        1. Initialize Video Upload (/rest/videos?action=initializeUpload)
        2. Upload Video Binary Chunks (PUT to uploadUrls)
        3. Create Post referencing the video URN (/rest/posts)
        """
        file_size = video_path.stat().st_size
        project_title = project_config.get("title", project_config.get("name", "Project Demo"))

        # Step 1: Initialize Video Upload
        logger.info("Step 1/3: Initializing video upload with LinkedIn Videos API...")
        init_url = "https://api.linkedin.com/rest/videos?action=initializeUpload"
        init_payload = {
            "initializeUploadRequest": {
                "owner": self.author_urn,
                "fileSizeBytes": file_size,
                "uploadCaptions": False,
                "uploadThumbnail": False
            }
        }

        headers = {**self.base_headers, "Content-Type": "application/json"}
        init_resp = requests.post(init_url, json=init_payload, headers=headers, timeout=30)

        if init_resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to initialize LinkedIn video upload: {init_resp.status_code} - {init_resp.text}"
            )

        init_data = init_resp.json().get("value", {})
        video_urn = init_data.get("video")
        upload_instructions = init_data.get("uploadInstructions", [])

        if not video_urn or not upload_instructions:
            raise RuntimeError(f"Invalid upload instructions received: {init_resp.text}")

        logger.info(f"Upload initialized. Video URN: {video_urn}")

        # Step 2: Upload Video Binary Chunks
        logger.info(f"Step 2/3: Uploading video binary ({round(file_size / (1024*1024), 2)} MB)...")
        uploaded_part_ids = []
        with open(video_path, "rb") as f:
            for i, part in enumerate(upload_instructions):
                upload_url = part.get("uploadUrl")
                first_byte = part.get("firstByte")
                last_byte = part.get("lastByte")
                chunk_len = last_byte - first_byte + 1

                f.seek(first_byte)
                chunk_data = f.read(chunk_len)

                put_headers = {
                    "Content-Type": "application/octet-stream"
                }
                logger.info(f"Uploading part {i+1}/{len(upload_instructions)} ({chunk_len} bytes)...")
                put_resp = requests.put(upload_url, data=chunk_data, headers=put_headers, timeout=60)
                if put_resp.status_code not in (200, 201, 204):
                    raise RuntimeError(f"Video chunk upload failed: {put_resp.status_code} - {put_resp.text}")
                etag = put_resp.headers.get("ETag", "")
                uploaded_part_ids.append(etag)

        logger.info(f"All {len(uploaded_part_ids)} parts uploaded. Finalizing video upload...")

        # Step 2.1: Finalize Upload with ETags
        finalize_url = "https://api.linkedin.com/rest/videos?action=finalizeUpload"
        finalize_payload = {
            "finalizeUploadRequest": {
                "video": video_urn,
                "uploadToken": init_data.get("uploadToken", ""),
                "uploadedPartIds": uploaded_part_ids
            }
        }
        fin_resp = requests.post(finalize_url, json=finalize_payload, headers=headers, timeout=30)
        if fin_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to finalize video upload: {fin_resp.status_code} - {fin_resp.text}")

        # Step 2.5: Poll video status until AVAILABLE (LinkedIn video processing transcode)
        logger.info("Waiting for LinkedIn to finalize video processing (checking status)...")
        import time
        from urllib.parse import quote
        encoded_urn = quote(video_urn, safe="")
        video_status_url = f"https://api.linkedin.com/rest/videos/{encoded_urn}"
        max_poll_sec = 90
        poll_start = time.time()
        is_available = False

        while time.time() - poll_start < max_poll_sec:
            try:
                status_resp = requests.get(video_status_url, headers=self.base_headers, timeout=15)
                if status_resp.status_code == 200:
                    v_status = status_resp.json().get("status", "")
                    logger.info(f"Video processing status: {v_status}")
                    if v_status == "AVAILABLE":
                        is_available = True
                        break
                    elif v_status in ("PROCESSING_FAILED", "FAILED"):
                        raise RuntimeError(f"LinkedIn video processing failed: {status_resp.text}")
            except Exception as pe:
                logger.debug(f"Status poll exception: {pe}")
            time.sleep(3)

        if not is_available:
            raise RuntimeError(f"Video {video_urn} failed to transition to AVAILABLE within {max_poll_sec}s.")

        # Step 3: Create Post referencing the uploaded Video URN
        logger.info("Step 3/3: Publishing post via LinkedIn Posts API...")
        posts_url = "https://api.linkedin.com/rest/posts"
        post_payload = {
            "author": self.author_urn,
            "commentary": post_text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "content": {
                "media": {
                    "title": project_title,
                    "id": video_urn
                }
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        post_resp = requests.post(posts_url, json=post_payload, headers=headers, timeout=30)
        if post_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create LinkedIn post: {post_resp.status_code} - {post_resp.text}")

        # LinkedIn returns post URN in 'x-restli-id' header or body
        post_urn = post_resp.headers.get("x-restli-id") or post_resp.headers.get("Location", "Unknown URN")
        logger.info(f"Post successfully published to LinkedIn! Post ID: {post_urn}")

        return {
            "status": "PUBLISHED",
            "video_urn": video_urn,
            "post_urn": post_urn,
            "published_at": datetime.now().isoformat()
        }

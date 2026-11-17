"""
Vercel Project Integration & Auto-Discovery Helper
Uses Vercel REST API to discover deployed projects and live URLs,
automatically integrating them into projects_config.json.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv

logger = logging.getLogger("Pipeline.Vercel")
load_dotenv()


class VercelManager:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("VERCEL_TOKEN", "")
        self.base_url = "https://api.vercel.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def is_configured(self) -> bool:
        return bool(self.token)

    def fetch_projects(self) -> List[Dict[str, Any]]:
        """Fetch all projects and their production URLs from Vercel."""
        if not self.is_configured():
            logger.warning("VERCEL_TOKEN not set in .env. Skipping Vercel sync.")
            return []

        url = f"{self.base_url}/v9/projects"
        try:
            resp = requests.get(url, headers=self.headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                projects = data.get("projects", [])
                results = []
                for p in projects:
                    p_name = p.get("name")
                    # Find production domain
                    prod_url = None
                    targets = p.get("targets", {})
                    if "production" in targets and targets["production"].get("url"):
                        prod_url = f"https://{targets['production']['url']}"
                    elif p.get("latestDeployments"):
                        latest = p["latestDeployments"][0].get("url")
                        if latest:
                            prod_url = f"https://{latest}"
                    else:
                        prod_url = f"https://{p_name}.vercel.app"

                    results.append({
                        "name": p_name,
                        "id": p.get("id"),
                        "live_url": prod_url,
                        "updated_at": p.get("updatedAt")
                    })
                logger.info(f"Retrieved {len(results)} projects from Vercel account.")
                return results
            else:
                logger.error(f"Vercel API error {resp.status_code}: {resp.text}")
                return []
        except Exception as e:
            logger.error(f"Failed to query Vercel API: {e}")
            return []

    def sync_to_projects_config(self, config_path: Path):
        """Merge discovered Vercel URLs into projects_config.json."""
        vercel_projects = self.fetch_projects()
        if not vercel_projects:
            return

        config_path = Path(config_path)
        if not config_path.exists():
            return

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        projects_list = data.get("projects", data if isinstance(data, list) else [])
        matched = 0

        for vp in vercel_projects:
            v_name = vp["name"].lower().replace("-", "_")
            for p in projects_list:
                p_name = p.get("name", "").lower().replace("-", "_")
                if v_name in p_name or p_name in v_name or p.get("vercel_project") == vp["name"]:
                    p["live_url"] = vp["live_url"]
                    matched += 1
                    logger.info(f"Linked Vercel URL '{vp['live_url']}' to project '{p.get('name')}'")
                    break

        # Save back
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"projects": projects_list}, f, indent=2)

        logger.info(f"Vercel Sync Complete: Matched {matched} projects with live URLs.")


if __name__ == "__main__":
    vm = VercelManager()
    if vm.is_configured():
        projs = vm.fetch_projects()
        print(f"Found {len(projs)} Vercel projects:")
        for p in projs:
            print(f" - {p['name']}: {p['live_url']}")
    else:
        print("Add VERCEL_TOKEN to .env to discover and sync Vercel projects.")

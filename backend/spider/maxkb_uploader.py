"""
Upload Markdown files to MaxKB knowledge base via Admin REST API.

Uses the session-token-based Admin API (community edition workaround):
  1. POST document/split       → upload file, get split content
  2. PUT  document/batch_create → create documents from split content

Auth: Authorization: Bearer <session_token>
Get session token: Login to MaxKB → F12 → Application → Cookies → Authorization
Paste into .env as MAXKB_SESSION_TOKEN (including "Bearer " prefix).

MaxKB deployed on a different machine? Just set MAXKB_BASE_URL and MAXKB_SESSION_TOKEN
in .env - no volume mounts or container access needed.
"""
import json
import time
import logging
from pathlib import Path
from typing import Optional, Set

import requests

from .config import SpiderConfig
from .file_manager import FileManager

logger = logging.getLogger(__name__)


class MaxKBUploader:
    """
    Uploads Markdown files to MaxKB knowledge base via Admin API.

    Two-step process:
      1. POST /admin/api/workspace/default/knowledge/{id}/document/split
         → Returns segmented document content
      2. PUT /admin/api/workspace/default/knowledge/{id}/document/batch_create
         → Creates documents from the split content (rename content→paragraphs)
    """

    def __init__(self):
        cfg = SpiderConfig
        self.base_url = cfg.MAXKB_BASE_URL.rstrip('/')
        self.session_token: str = os.getenv("MAXKB_SESSION_TOKEN", "")
        self.dataset_id = cfg.MAXKB_DATASET_ID
        self.output_dir = cfg.OUTPUT_DIR
        self.file_mgr = FileManager(cfg.UPLOADED_RECORD)

        if not self.session_token:
            logger.warning(
                "MAXKB_SESSION_TOKEN not set in .env. "
                "Upload will fail. Get it from browser cookies after logging into MaxKB."
            )

    @property
    def headers(self) -> dict:
        return {
            "Authorization": self.session_token,
        }

    def split_document(self, filepath: Path, filename: str) -> Optional[list]:
        """
        Step 1: Upload file for splitting.

        POST /admin/api/workspace/default/knowledge/{id}/document/split

        Returns the 'data' list from the response (list of {name, content: [{title, content}]}).
        """
        url = f"{self.base_url}/admin/api/workspace/default/knowledge/{self.dataset_id}/document/split"
        try:
            with open(filepath, 'rb') as fh:
                resp = requests.post(
                    url,
                    headers=self.headers,
                    files={"file": (filename, fh, 'text/markdown')},
                    timeout=120,
                )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 200:
                    return result["data"]
                else:
                    logger.error(f"Split failed: {result.get('message')}")
                    return None
            else:
                logger.error(f"Split HTTP {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Split error: {e}")
            return None

    def batch_create(self, documents: list) -> bool:
        """
        Step 2: Create documents from split content.

        PUT /admin/api/workspace/default/knowledge/{id}/document/batch_create

        Args:
            documents: List from split response, transformed (content→paragraphs).
        """
        # Transform: rename "content" key to "paragraphs" in each document
        payload = []
        for doc in documents:
            item = {"name": doc["name"], "paragraphs": doc.get("content", doc.get("paragraphs", []))}
            payload.append(item)

        url = f"{self.base_url}/admin/api/workspace/default/knowledge/{self.dataset_id}/document/batch_create"
        try:
            resp = requests.put(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 200:
                    created = result.get("data", [])
                    for doc in created:
                        logger.info(f"  Created: {doc.get('name')} (id={doc.get('id')})")
                    return True
                else:
                    logger.error(f"Batch create failed: {result.get('message')}")
                    return False
            else:
                logger.error(f"Batch create HTTP {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Batch create error: {e}")
            return False

    def upload_file(self, filepath: Path, filename: str) -> bool:
        """
        Upload a single file: split → batch_create.

        Returns True if the document was successfully created.
        """
        # Step 1: Split
        documents = self.split_document(filepath, filename)
        if not documents:
            return False

        # Step 2: Create
        if not self.batch_create(documents):
            return False

        self.file_mgr.add(filename)
        return True

    def upload_folder(self, folder: Optional[Path] = None) -> dict:
        """
        Upload all new Markdown files from the output directory.

        Each file goes through split → batch_create.

        Returns:
            {success: int, failed: int, skipped: int, total: int}
        """
        if folder is None:
            folder = self.output_dir

        if not folder.exists():
            logger.error(f"Folder not found: {folder}")
            return {"success": 0, "failed": 0, "skipped": 0, "total": 0}

        all_files = list(folder.rglob("*.md"))
        if not all_files:
            logger.warning(f"No .md files in {folder}")
            return {"success": 0, "failed": 0, "skipped": 0, "total": 0}

        uploaded: Set[str] = self.file_mgr.get_uploaded()
        to_upload = [f for f in all_files if f.name not in uploaded]

        logger.info(f"Found {len(all_files)} files, {len(to_upload)} new")

        success = 0
        failed = 0

        for i, filepath in enumerate(to_upload):
            filename = filepath.name
            logger.info(f"[{i+1}/{len(to_upload)}] {filename}")

            if self.upload_file(filepath, filename):
                success += 1
            else:
                failed += 1

            if i < len(to_upload) - 1:
                time.sleep(1)

        result = {
            "success": success,
            "failed": failed,
            "skipped": len(all_files) - len(to_upload),
            "total": len(all_files),
        }
        logger.info(f"Upload done: {result}")
        return result


# Needed for os.getenv at module level
import os

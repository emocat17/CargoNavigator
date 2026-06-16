"""
Track uploaded files to avoid duplicate uploads.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Set


def sort_by_date(file_list: list) -> list:
    """Sort file list by date extracted from filename, newest first."""
    def extract_datetime(filename: str):
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            dt_str = f"{date_str} {time_str.replace('-', ':')}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return datetime.min

    return sorted(file_list, key=extract_datetime, reverse=True)


class FileManager:
    """Manages uploaded file tracking via a local JSON record."""

    def __init__(self, record_path: Path):
        self.record_path = record_path

    def _read(self) -> list:
        if not self.record_path.exists():
            return []
        with open(self.record_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write(self, files: list):
        self.record_path.parent.mkdir(parents=True, exist_ok=True)
        sorted_files = sort_by_date(files)
        with open(self.record_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_files, f, ensure_ascii=False, indent=2)

    def get_uploaded(self) -> Set[str]:
        """Return set of uploaded filenames."""
        return set(self._read())

    def is_uploaded(self, filename: str) -> bool:
        """Check if a file has been uploaded."""
        return filename in self._read()

    def add(self, filename: str) -> bool:
        """Add a file to the uploaded record. Returns False if already present."""
        files = self._read()
        if filename in files:
            return False
        files.append(filename)
        self._write(files)
        return True

    def count(self) -> int:
        return len(self._read())

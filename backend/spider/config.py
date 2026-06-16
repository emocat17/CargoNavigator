"""
Spider configuration - reads from project root .env file.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (two levels up from backend/spider/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class SpiderConfig:
    """Spider configuration from environment variables."""

    # ---- Paths ----
    BASE_DIR: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = BASE_DIR / "data"
    JSON_DIR: Path = DATA_DIR / "json"
    OUTPUT_DIR: Path = DATA_DIR / "road_details"
    UPLOADED_RECORD: Path = DATA_DIR / ".uploaded_files.json"

    # ---- FJETC API (AES encrypted) ----
    FJETC_PUBLIC_KEY: str = "f1ed4UgYNLWSXtR0kHKZcqFFhyakX6WH"
    FJETC_API_URL: str = "https://www.fjetc.com/mgsfwq/FunctionList/Traffic/getTrafficMessage"

    # ---- MaxKB ----
    MAXKB_BASE_URL: str = os.getenv("MAXKB_BASE_URL", "http://localhost:8080")
    MAXKB_API_KEY: str = os.getenv("MAXKB_API_KEY", "")
    # Knowledge base / dataset ID - the traffic knowledge base
    # This is the knowledge base ID (not the application API key)
    MAXKB_DATASET_ID: str = os.getenv("MAXKB_DATASET_ID", "019ecdfe-98e1-7de1-be26-1831f2be7242")

    # ---- Crawler Settings ----
    REQUEST_TIMEOUT: int = 30
    PAGE_SIZE: int = 500
    MAX_PAGES: int = 300
    REQUEST_DELAY: float = 0.5  # seconds between pages

    # ---- Upload Settings ----
    UPLOAD_BATCH_SIZE: int = 20
    WAIT_FOR_INDEXING: bool = True
    INDEXING_MAX_WAIT: int = 300  # seconds

    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.JSON_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing items."""
        missing = []
        if not cls.MAXKB_API_KEY:
            missing.append("MAXKB_API_KEY")
        if not cls.MAXKB_DATASET_ID:
            missing.append("MAXKB_DATASET_ID")
        return missing

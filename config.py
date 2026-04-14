import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_FILE_PATH = os.getenv("REAL_ESTATE_DB_PATH", str(BASE_DIR / "real_estate.db"))
MEDIA_DIR = os.getenv("REAL_ESTATE_MEDIA_DIR", str(BASE_DIR / "uploads" / "media"))

API_HOST = os.getenv("REAL_ESTATE_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("REAL_ESTATE_API_PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("REAL_ESTATE_STREAMLIT_PORT", "8501"))

AI_API_KEY = os.getenv("REAL_ESTATE_AI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
AI_BASE_URL = os.getenv("REAL_ESTATE_AI_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
AI_MODEL = os.getenv("REAL_ESTATE_AI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

LOG_LEVEL = os.getenv("REAL_ESTATE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

"""Central settings. Values come from environment variables (or Streamlit secrets in the app)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path=ROOT / ".env"):
    """Read KEY=VALUE lines from .env (without overriding real environment variables)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value.strip() and not os.getenv(key.strip()):
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


_load_dotenv()

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.getenv("SB_DB_PATH", DATA_DIR / "olist.duckdb"))

SEMANTIC_CURATED = ROOT / "semantic" / "olist.yaml"
SEMANTIC_AUTO = ROOT / "semantic" / "olist_auto.yaml"
QUESTIONS_FILE = ROOT / "benchmark" / "questions.json"
RESULTS_DIR = ROOT / "results"
LOG_DB = Path(os.getenv("SB_LOG_DB", ROOT / "logs" / "query_log.sqlite"))

# Safety limits for live queries
MAX_ROWS = int(os.getenv("SB_MAX_ROWS", "1000"))
QUERY_TIMEOUT_SEC = float(os.getenv("SB_QUERY_TIMEOUT", "20"))

# Default AI provider for the live app (free option)
DEFAULT_PROVIDER = os.getenv("SB_PROVIDER", "groq")
DEFAULT_MODEL = os.getenv("SB_MODEL", "")

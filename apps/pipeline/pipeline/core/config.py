import os
from pathlib import Path

from dotenv import load_dotenv
from firms_shared.constants import DEFAULT_FIRMS_BASE_URL

load_dotenv()

BASE_URL = os.getenv("FIRMS_BASE_URL", DEFAULT_FIRMS_BASE_URL)
API_BASE_URL = f"{BASE_URL}/api"

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")
if not FIRMS_MAP_KEY:
    raise RuntimeError("FIRMS_MAP_KEY is required in the environment or .env file.")

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
META_DIR = Path(os.getenv("META_DIR", str(DATA_DIR / "_meta")))
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(DATA_DIR / "temp")))
RAW_META_DIR = Path(os.getenv("RAW_META_DIR", str(TEMP_DIR / "raw_meta")))
RAW_DIR = Path(os.getenv("RAW_DIR", str(DATA_DIR / "raw")))

DB_PATH = Path(os.getenv("PIPELINE_DB_PATH", str(DATA_DIR / "pipeline.db")))
DATABASE_URL = f"sqlite:///{DB_PATH}"

COUNTRY_SUMMARY_INDEX_PATH = "data/country/yearly_summary_files.txt"
MAPKEY_STATUS_URL = f"{BASE_URL}/mapserver/mapkey_status/"

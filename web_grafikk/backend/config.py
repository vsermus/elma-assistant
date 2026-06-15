import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
ENV_PATH = ROOT / ".env"
LOAD_SCRIPT = ROOT / "scripts" / "load" / "load_data.py"

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production-change-me-in-production-32bytes")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

TOKEN = os.environ.get("ELMA_TOKEN", "")
if not TOKEN and ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == "ELMA_TOKEN":
                TOKEN = v.strip().strip('"').strip("'")

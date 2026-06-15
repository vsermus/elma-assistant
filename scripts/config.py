import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(ROOT, "data")
DATA_TENDER_DIR = os.path.join(DATA_DIR, "tender")
DATA_WORKS_DIR = os.path.join(DATA_DIR, "works")
DATA_USERS_DIR = os.path.join(DATA_DIR, "users")
DATA_ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

DASHBOARDS_DIR = os.path.join(ROOT, "dashboards")
REPORTS_DIR = os.path.join(ROOT, "reports")
CONFIG_DIR = os.path.join(ROOT, "config")
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
HISTORY_DIR = os.path.join(ROOT, "history")

ENV_PATH = os.path.join(ROOT, ".env")
ENTITIES_CONFIG = os.path.join(CONFIG_DIR, "entities.json")

# карта "старых" имён файлов к полным путям (для обратной совместимости)
FILES = {
    "works_raw": os.path.join(DATA_WORKS_DIR, "all_works_with_status.json"),
    "works_processed": os.path.join(DATA_WORKS_DIR, "all_works.json"),
    "tenders_all": os.path.join(DATA_TENDER_DIR, "all_tenders.json"),
    "tenders_consolidated": os.path.join(DATA_TENDER_DIR, "all_tenders_consolidated.json"),
    "users": os.path.join(DATA_USERS_DIR, "users.json"),
    "companies": os.path.join(DATA_DIR, "companies.json"),
    "statusy": os.path.join(DATA_DIR, "statusy.json"),
}

import subprocess
import sys

from .config import LOAD_SCRIPT


def run_update():
    try:
        args = [sys.executable or "python", str(LOAD_SCRIPT)]
        subprocess.run(args, capture_output=True, text=True, timeout=300)
        return True
    except Exception:
        return False


def setup_scheduler(app):
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_update, "interval", hours=24, id="daily_update")
        scheduler.start()
    except ImportError:
        pass

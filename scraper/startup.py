import os
import threading
import time
from datetime import datetime, timedelta, timezone


_scraper_started = False
_scraper_lock = threading.Lock()
_status_lock = threading.Lock()
_repeat_delay_seconds = 60
_scraper_status = {
    "enabled": True,
    "is_running": False,
    "cycle": 0,
    "processed": 0,
    "total": 0,
    "percent": 0,
    "current_source": "",
    "current_url": "",
    "message": "Scraper has not started yet.",
    "last_started_at": "",
    "last_completed_at": "",
    "next_run_at": "",
    "error": "",
}


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _set_status(**updates):
    with _status_lock:
        _scraper_status.update(updates)


def get_scraper_status():
    with _status_lock:
        return dict(_scraper_status)


def update_scraper_progress(processed, total, source="", url=""):
    percent = 100 if total == 0 else round((processed / total) * 100)
    message = (
        "Scraping complete."
        if total and processed >= total
        else f"Scraping {source}..."
        if source
        else "Scraping started."
    )
    _set_status(
        processed=processed,
        total=total,
        percent=max(0, min(percent, 100)),
        current_source=source,
        current_url=url,
        message=message,
    )


def _run_scraper_loop():
    from .runner import run_all_scrapers

    while True:
        started_at = _now()
        current = get_scraper_status()
        _set_status(
            enabled=True,
            is_running=True,
            cycle=current["cycle"] + 1,
            processed=0,
            total=0,
            percent=0,
            current_source="",
            current_url="",
            message="Scraping started.",
            last_started_at=_iso(started_at),
            next_run_at="",
            error="",
        )

        try:
            run_all_scrapers(progress_callback=update_scraper_progress)
            completed_at = _now()
            next_run_at = completed_at + timedelta(seconds=_repeat_delay_seconds)
            _set_status(
                is_running=False,
                percent=100,
                message="Scraping complete. Next run starts in 1 minute.",
                last_completed_at=_iso(completed_at),
                next_run_at=_iso(next_run_at),
                error="",
            )
            print("Automatic scraping completed successfully!")
        except Exception as exc:
            completed_at = _now()
            next_run_at = completed_at + timedelta(seconds=_repeat_delay_seconds)
            _set_status(
                is_running=False,
                message="Scraping failed. Next run starts in 1 minute.",
                last_completed_at=_iso(completed_at),
                next_run_at=_iso(next_run_at),
                error=str(exc),
            )
            print(f"Automatic scraping failed: {exc}")

        time.sleep(_repeat_delay_seconds)


def start_scraper_once():
    global _scraper_started

    if os.environ.get("GOVSCRAPER_AUTO_START", "1").lower() in {"0", "false", "no"}:
        _set_status(enabled=False, message="Automatic scraping is disabled.")
        return False

    with _scraper_lock:
        if _scraper_started:
            return False
        _scraper_started = True

        thread = threading.Thread(target=_run_scraper_loop, name="govscraper-auto-scraper")
        thread.daemon = True
        thread.start()
        print("Automatic scraping started in background.")
        return True

import os
import threading


_scraper_started = False
_scraper_lock = threading.Lock()


def _run_scraper():
    from .runner import run_all_scrapers

    try:
        run_all_scrapers()
        print("Automatic scraping completed successfully!")
    except Exception as exc:
        print(f"Automatic scraping failed: {exc}")


def start_scraper_once():
    global _scraper_started

    if os.environ.get("GOVSCRAPER_AUTO_START", "1").lower() in {"0", "false", "no"}:
        return False

    with _scraper_lock:
        if _scraper_started:
            return False
        _scraper_started = True

        thread = threading.Thread(target=_run_scraper, name="govscraper-auto-scraper")
        thread.daemon = True
        thread.start()
        print("Automatic scraping started in background.")
        return True

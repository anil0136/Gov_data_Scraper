from django.apps import AppConfig
import os
import sys


class ScraperConfig(AppConfig):
    name = 'scraper'

    def _should_start_scraper(self):
        executable = os.path.basename(sys.argv[0]).lower()
        command = sys.argv[1] if len(sys.argv) > 1 else ""

        if command == "runserver":
            auto_start = os.environ.get("GOVSCRAPER_AUTO_START", "0").lower()
            return os.environ.get("RUN_MAIN") == "true" and auto_start in {"1", "true", "yes", "on"}

        return "gunicorn" in executable

    def ready(self):
        if not self._should_start_scraper():
            return

        from .startup import start_scraper_once

        start_scraper_once()

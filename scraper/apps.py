from django.apps import AppConfig
import os
import sys


class ScraperConfig(AppConfig):
    name = 'scraper'

    def ready(self):
        if "runserver" not in sys.argv:
            return

        if os.environ.get("RUN_MAIN") != "true":
            return

        from .startup import start_scraper_once

        start_scraper_once()

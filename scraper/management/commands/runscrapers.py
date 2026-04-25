from django.core.management.base import BaseCommand
from scraper.runner import run_all_scrapers

class Command(BaseCommand):
    help = 'Runs all scrapers to fetch and update schemes and scholarships.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting the scrapers...'))
        try:
            run_all_scrapers()
            self.stdout.write(self.style.SUCCESS('Successfully completed scraping!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error during scraping: {e}'))

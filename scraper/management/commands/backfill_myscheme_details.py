import time
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import OperationalError, connection

from scraper.models import MyScheme
from scraper.scrapers.common import get_session
from scraper.scrapers.myscheme import MYSCHEME_API_KEY, _fetch_detail, _merge_detail


class Command(BaseCommand):
    help = "Backfills missing myScheme detail fields for records that only have listing data."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--delay", type=float, default=1.0)

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA busy_timeout = 15000")

        session = get_session(extra_headers={
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.myscheme.gov.in",
            "Referer": "https://www.myscheme.gov.in/",
            "x-api-key": MYSCHEME_API_KEY,
        })

        ids = list(
            MyScheme.objects.filter(raw_data={})
            .order_by("id")
            .values_list("id", flat=True)
        )
        if options["limit"]:
            ids = ids[:options["limit"]]

        total = len(ids)
        updated = 0
        failed = 0

        for index, row_id in enumerate(ids, 1):
            row = MyScheme.objects.get(id=row_id)
            slug = urlparse(row.url or "").path.rstrip("/").split("/")[-1]
            if not slug:
                failed += 1
                continue

            parsed = {
                "title": row.title,
                "description": row.description or "",
                "eligibility": row.eligibility or "",
                "benefits": row.benefits or "",
                "category": row.category or "MyScheme",
                "ministry": row.ministry or "",
                "department": row.department or "",
                "level": row.level or "",
                "tags": row.tags or "",
                "application_process": row.application_process or "",
                "documents": row.documents or "",
                "references": row.references or "",
                "raw_data": row.raw_data or {},
                "url": row.url,
                "_slug": slug,
            }

            try:
                detail = _fetch_detail(session, slug)
                parsed = _merge_detail(parsed, detail)
                for key, value in parsed.items():
                    if key != "_slug" and hasattr(row, key):
                        setattr(row, key, value)
                row.save(update_fields=[
                    "title",
                    "description",
                    "eligibility",
                    "benefits",
                    "category",
                    "ministry",
                    "department",
                    "level",
                    "tags",
                    "application_process",
                    "documents",
                    "references",
                    "raw_data",
                    "url",
                ])
                updated += 1
            except OperationalError as exc:
                failed += 1
                self.stderr.write(f"DB locked for {row_id} {slug}: {exc}")
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Failed {row_id} {slug}: {type(exc).__name__}: {exc}")

            if index % 25 == 0 or index == total:
                self.stdout.write(f"progress {index}/{total}, updated={updated}, failed={failed}")
            time.sleep(options["delay"])

        self.stdout.write(self.style.SUCCESS(f"done total={total}, updated={updated}, failed={failed}"))

import time
from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from scraper.mongo import find_records, upsert_one
from scraper.scrapers.common import get_session
from scraper.scrapers.myscheme import MYSCHEME_API_KEY, _fetch_detail, _merge_detail


class Command(BaseCommand):
    help = "Backfills missing myScheme detail fields for records that only have listing data."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--delay", type=float, default=1.0)

    def handle(self, *args, **options):
        session = get_session(extra_headers={
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.myscheme.gov.in",
            "Referer": "https://www.myscheme.gov.in/",
            "x-api-key": MYSCHEME_API_KEY,
        })

        rows = find_records("myscheme", {"raw_data": {}})
        if options["limit"]:
            rows = rows[:options["limit"]]

        total = len(rows)
        updated = 0
        failed = 0

        for index, row in enumerate(rows, 1):
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
                parsed.pop("_slug", None)
                upsert_one("myscheme", {"_id": row.data["_id"]}, parsed)
                updated += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Failed {row.id} {slug}: {type(exc).__name__}: {exc}")

            if index % 25 == 0 or index == total:
                self.stdout.write(f"progress {index}/{total}, updated={updated}, failed={failed}")
            time.sleep(options["delay"])

        self.stdout.write(self.style.SUCCESS(f"done total={total}, updated={updated}, failed={failed}"))

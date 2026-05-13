import time

from django.db import OperationalError, close_old_connections, transaction
from django.db.models import Q

from .models import *


BAD_INDIA_TITLE_PARTS = (
    "request id:",
    "translationdisclaimer",
    "translations of the content",
    "you need to enable javascript",
    "loading...",
    "content sources",
    "screen reader",
    "india portal 2.0 brochure",
    "no data found",
    "view more",
    "myscheme.gov.in/contact",
)

BAD_SCHOLARSHIP_TITLES = {
    "log in",
    "sign up",
    "close",
    "scholarships",
    "by degree",
    "by subject",
    "by university",
    "by country of interest",
    "loans",
    "more...",
    "whatsapp channel",
}

BAD_SCHOLARSHIP_TITLE_PARTS = (
    "top banks for education loan",
    "countries more",
)

BAD_GOV_TITLE_PARTS = (
    "showrecentpopularfilters",
    "homeall categories",
)


def _retry_db_operation(operation, retries=6, delay=1.0):
    last_error = None
    for attempt in range(retries):
        try:
            close_old_connections()
            return operation()
        except OperationalError as exc:
            if "database is locked" not in str(exc).lower():
                raise
            last_error = exc
            time.sleep(delay * (attempt + 1))
    raise last_error


def _print_save_progress(label, saved, total):
    if saved == total or saved % 500 == 0:
        print(f"    {label} storing progress: {saved}/{total}")


def _limit_json_depth(value, max_depth=20):
    if max_depth <= 0:
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _limit_json_depth(item, max_depth - 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_limit_json_depth(item, max_depth - 1) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _mysql_safe_item(item):
    safe_item = item.copy()
    if "raw_data" in safe_item:
        safe_item["raw_data"] = _limit_json_depth(safe_item.get("raw_data") or {})
    return safe_item


def _cleanup_india_rows():
    for item in IndiaScheme.objects.all():
        title = (item.title or "").strip().lower()
        if not title or title.startswith(("http://", "https://", "www.")):
            item.delete()
            continue
        if any(part in title for part in BAD_INDIA_TITLE_PARTS):
            item.delete()


def _cleanup_gov_rows():
    GovService.objects.filter(Q(title__isnull=True) | Q(title="")).delete()
    empty_detail = (
        (Q(description__isnull=True) | Q(description=""))
        & (Q(service_type__isnull=True) | Q(service_type=""))
        & (Q(department__isnull=True) | Q(department=""))
    )
    GovService.objects.filter(empty_detail).delete()
    for part in BAD_GOV_TITLE_PARTS:
        GovService.objects.filter(title__icontains=part).delete()


def _chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _bulk_save_gov_services(items, batch_size=500):
    titles = [item["title"] for item in items]
    existing_by_title = {}

    for title_batch in _chunks(titles, batch_size):
        for service in GovService.objects.filter(title__in=title_batch).order_by("id"):
            existing_by_title.setdefault(service.title, service)

    create_items = []
    update_items = []
    update_fields = ["service_type", "department", "description", "url"]

    for item in items:
        service = existing_by_title.get(item["title"])
        if service is None:
            create_items.append(GovService(**item))
            continue

        for field in update_fields:
            setattr(service, field, item.get(field))
        update_items.append(service)

    with transaction.atomic():
        for create_batch in _chunks(create_items, batch_size):
            GovService.objects.bulk_create(create_batch, batch_size=batch_size)
        for update_batch in _chunks(update_items, batch_size):
            GovService.objects.bulk_update(update_batch, update_fields, batch_size=batch_size)

    return len(create_items), len(update_items)


def _cleanup_myscheme_rows():
    for item in MyScheme.objects.all():
        title = (item.title or "").strip()
        description = (item.description or "").strip()
        eligibility = (item.eligibility or "").strip()
        benefits = (item.benefits or "").strip()

        if not title:
            item.delete()
            continue

        if not any([description, eligibility, benefits]):
            item.delete()


def _cleanup_scholarship_rows():
    for item in Scholarship.objects.all():
        title = (item.title or "").strip()
        lowered = title.lower()
        url = (item.url or "").strip().lower()
        provider = (item.provider or "").strip()
        amount = (item.amount or "").strip()
        deadline = (item.deadline or "").strip()
        image_url = (item.image_url or "").strip()
        has_specific_provider = provider not in {"", "WeMakeScholars", "Buddy4Study"}

        if not title:
            item.delete()
            continue

        if lowered in BAD_SCHOLARSHIP_TITLES:
            item.delete()
            continue

        if any(part in lowered for part in BAD_SCHOLARSHIP_TITLE_PARTS):
            item.delete()
            continue

        # Old broken rows were saved from listing pages without any real metadata.
        if (
            url in {
                "https://www.wemakescholars.com/scholarship",
                "https://www.buddy4study.com/scholarships",
            }
            and not any([has_specific_provider, amount, deadline, image_url])
        ):
            item.delete()
            continue


def save_umang(data):
    for item in data:
        _retry_db_operation(
            lambda item=item: UmangScheme.objects.update_or_create(
                title=item["title"],
                defaults=item,
            )
        )

def save_gov(data):
    total = len(data)
    print(f"    GOV storing {total} items to MySQL...")
    _retry_db_operation(_cleanup_gov_rows)
    clean_items = []

    for item in data:
        title = (item.get("title") or "").strip()
        lowered = title.lower()
        has_detail = any(
            [
                (item.get("description") or "").strip(),
                (item.get("service_type") or "").strip(),
                (item.get("department") or "").strip(),
            ]
        )
        if any(part in lowered for part in BAD_GOV_TITLE_PARTS) or not has_detail:
            continue

        clean_items.append(item)

    created, updated = _retry_db_operation(lambda: _bulk_save_gov_services(clean_items))
    print(
        "    GOV MySQL bulk save complete: "
        f"{created} created, {updated} updated."
    )

def save_myscheme(data):
    _retry_db_operation(_cleanup_myscheme_rows)
    for item in data:
        item = _mysql_safe_item(item)
        has_detail = any(
            [
                (item.get("description") or "").strip(),
                (item.get("eligibility") or "").strip(),
                (item.get("benefits") or "").strip(),
            ]
        )
        if not has_detail:
            continue

        _retry_db_operation(
            lambda item=item: MyScheme.objects.update_or_create(
                title=item["title"],
                defaults=item,
            )
        )

def save_india(data):
    _retry_db_operation(_cleanup_india_rows)
    for item in data:
        _retry_db_operation(
            lambda item=item: IndiaScheme.objects.update_or_create(
                title=item["title"],
                defaults=item,
            )
        )

def save_scholarship(data):
    _retry_db_operation(_cleanup_scholarship_rows)
    for item in data:
        scholarship_defaults = {
            "provider": item.get("provider"),
            "deadline": item.get("deadline"),
            "amount": item.get("amount"),
            "image_url": item.get("image_url"),
            "url": item.get("url"),
        }
        _retry_db_operation(
            lambda item=item, scholarship_defaults=scholarship_defaults: Scholarship.objects.update_or_create(
                title=item["title"],
                defaults=scholarship_defaults,
            )
        )

def save_grants(data):
    for item in data:
        grant_defaults = {
            "organization": item.get("organization"),
            "description": item.get("description"),
            "funding_amount": item.get("funding_amount"),
            "url": item.get("url"),
        }
        _retry_db_operation(
            lambda item=item, grant_defaults=grant_defaults: Grant.objects.update_or_create(
                title=item["title"],
                defaults=grant_defaults,
            )
        )


def save_tender_listings(data):
    for item in data:
        item = _mysql_safe_item(item)
        lookup = {"source": item["source"]}
        external_id = item.get("external_id")
        if external_id:
            lookup["external_id"] = external_id
        else:
            lookup["title"] = item["title"]
            lookup["url"] = item["url"]

        _retry_db_operation(
            lambda lookup=lookup, item=item: TenderListing.objects.update_or_create(
                **lookup,
                defaults=item,
            )
        )

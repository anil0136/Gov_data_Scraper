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


def _cleanup_india_rows():
    for item in IndiaScheme.objects.all():
        title = (item.title or "").strip().lower()
        if not title or title.startswith(("http://", "https://", "www.")):
            item.delete()
            continue
        if any(part in title for part in BAD_INDIA_TITLE_PARTS):
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
        UmangScheme.objects.update_or_create(
            title=item["title"],
            defaults=item
        )

def save_gov(data):
    for item in data:
        GovService.objects.update_or_create(
            title=item["title"],
            defaults=item
        )

def save_myscheme(data):
    for item in data:
        MyScheme.objects.update_or_create(
            title=item["title"],
            defaults=item
        )

def save_india(data):
    _cleanup_india_rows()
    for item in data:
        IndiaScheme.objects.update_or_create(
            title=item["title"],
            defaults=item
        )

def save_scholarship(data):
    _cleanup_scholarship_rows()
    for item in data:
        Scholarship.objects.update_or_create(
            title=item["title"],
            defaults={
                "provider": item.get("provider"),
                "deadline": item.get("deadline"),
                "amount": item.get("amount"),
                "image_url": item.get("image_url"),
                "url": item.get("url"),
            }
        )

def save_grants(data):
    for item in data:
        Grant.objects.update_or_create(
            title=item["title"],
            defaults={
                "organization": item.get("organization"),
                "description": item.get("description"),
                "funding_amount": item.get("funding_amount"),
                "url": item.get("url"),
            }
        )


def save_tender_listings(data):
    for item in data:
        lookup = {"source": item["source"]}
        external_id = item.get("external_id")
        if external_id:
            lookup["external_id"] = external_id
        else:
            lookup["title"] = item["title"]
            lookup["url"] = item["url"]

        TenderListing.objects.update_or_create(
            **lookup,
            defaults=item,
        )

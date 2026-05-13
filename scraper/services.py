import re

from .mongo import delete_by_id, delete_many, find_records, upsert_one


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


def _mongo_safe_item(item):
    safe_item = item.copy()
    if "raw_data" in safe_item:
        safe_item["raw_data"] = _limit_json_depth(safe_item.get("raw_data") or {})
    return safe_item


def _case_regex(value):
    return re.compile(re.escape(value), re.IGNORECASE)


def _delete_matching(kind, predicate):
    for item in find_records(kind):
        if predicate(item):
            delete_by_id(kind, item.data["_id"])


def _cleanup_india_rows():
    def should_delete(item):
        title = (item.title or "").strip().lower()
        return (
            not title
            or title.startswith(("http://", "https://", "www."))
            or any(part in title for part in BAD_INDIA_TITLE_PARTS)
        )

    _delete_matching("india", should_delete)


def _cleanup_gov_rows():
    delete_many("gov", {"$or": [{"title": {"$exists": False}}, {"title": ""}, {"title": None}]})
    delete_many(
        "gov",
        {
            "$and": [
                {"$or": [{"description": {"$exists": False}}, {"description": ""}, {"description": None}]},
                {"$or": [{"service_type": {"$exists": False}}, {"service_type": ""}, {"service_type": None}]},
                {"$or": [{"department": {"$exists": False}}, {"department": ""}, {"department": None}]},
            ]
        },
    )
    for part in BAD_GOV_TITLE_PARTS:
        delete_many("gov", {"title": _case_regex(part)})


def _cleanup_myscheme_rows():
    def should_delete(item):
        title = (item.title or "").strip()
        description = (item.description or "").strip()
        eligibility = (item.eligibility or "").strip()
        benefits = (item.benefits or "").strip()
        return not title or not any([description, eligibility, benefits])

    _delete_matching("myscheme", should_delete)


def _cleanup_scholarship_rows():
    def should_delete(item):
        title = (item.title or "").strip()
        lowered = title.lower()
        url = (item.url or "").strip().lower()
        provider = (item.provider or "").strip()
        amount = (item.amount or "").strip()
        deadline = (item.deadline or "").strip()
        image_url = (item.image_url or "").strip()
        has_specific_provider = provider not in {"", "WeMakeScholars", "Buddy4Study"}

        if not title:
            return True
        if lowered in BAD_SCHOLARSHIP_TITLES:
            return True
        if any(part in lowered for part in BAD_SCHOLARSHIP_TITLE_PARTS):
            return True
        return (
            url
            in {
                "https://www.wemakescholars.com/scholarship",
                "https://www.buddy4study.com/scholarships",
            }
            and not any([has_specific_provider, amount, deadline, image_url])
        )

    _delete_matching("scholarships", should_delete)


def _upsert_by_title(kind, item):
    result = upsert_one(kind, {"title": item["title"]}, item)
    return (1, 0) if result.upserted_id else (0, result.modified_count)


def save_umang(data):
    for item in data:
        _upsert_by_title("umang", item)


def save_gov(data):
    total = len(data)
    print(f"    GOV storing {total} items to MongoDB...")
    _cleanup_gov_rows()
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

    created = 0
    updated = 0
    for item in clean_items:
        item_created, item_updated = _upsert_by_title("gov", item)
        created += item_created
        updated += item_updated

    print(
        "    GOV MongoDB save complete: "
        f"{created} created, {updated} updated."
    )


def save_myscheme(data):
    _cleanup_myscheme_rows()
    for item in data:
        item = _mongo_safe_item(item)
        has_detail = any(
            [
                (item.get("description") or "").strip(),
                (item.get("eligibility") or "").strip(),
                (item.get("benefits") or "").strip(),
            ]
        )
        if has_detail:
            _upsert_by_title("myscheme", item)


def save_india(data):
    _cleanup_india_rows()
    for item in data:
        _upsert_by_title("india", item)


def save_scholarship(data):
    _cleanup_scholarship_rows()
    for item in data:
        scholarship_item = {
            "title": item["title"],
            "provider": item.get("provider"),
            "deadline": item.get("deadline"),
            "amount": item.get("amount"),
            "image_url": item.get("image_url"),
            "url": item.get("url"),
        }
        _upsert_by_title("scholarships", scholarship_item)


def save_grants(data):
    for item in data:
        grant_item = {
            "title": item["title"],
            "organization": item.get("organization"),
            "description": item.get("description"),
            "funding_amount": item.get("funding_amount"),
            "url": item.get("url"),
        }
        _upsert_by_title("grants", grant_item)


def save_tender_listings(data):
    for item in data:
        item = _mongo_safe_item(item)
        lookup = {"source": item["source"]}
        external_id = item.get("external_id")
        if external_id:
            lookup["external_id"] = external_id
        else:
            lookup["title"] = item["title"]
            lookup["url"] = item["url"]
            item["external_id"] = None

        upsert_one("tenders", lookup, item)

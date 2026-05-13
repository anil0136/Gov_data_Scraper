import time
from urllib.parse import parse_qs, urlparse

from .common import absolute_url, clean_text, get_session, get_soup, is_good_title, unique_items


INDIA_SCHEMES_URL = "https://www.india.gov.in/my-government/schemes?page=1"
INDIA_SEARCH_API_URL = "https://www.india.gov.in/my-government/schemes/search/dataservices/getschemes"
INDIA_PAGE_SIZE = 100


def _category_from_url(url):
    query = parse_qs(urlparse(url).query)
    category_names = query.get("schemeCategoryName")
    if category_names:
        return clean_text(category_names[0])
    return "India Portal"


def _parse_featured_schemes(soup, base_url, category):
    data = []

    for link in soup.select("a[href]"):
        href = link.get("href")
        if not href or not href.startswith("http"):
            continue

        title = clean_text(link.get_text(" ", strip=True)).replace("Loading... ", "")
        lowered = title.lower()
        if not is_good_title(title, min_words=3):
            continue
        if "myscheme.gov.in/contact" in href:
            continue
        if "cpgrams" in lowered:
            continue
        if "screen reader" in lowered or "translation disclaimer" in lowered:
            continue

        data.append({
            "title": title,
            "description": "Featured on the National Portal of India schemes page.",
            "ministry": "National Portal of India",
            "category": category or "India Portal",
            "url": absolute_url(base_url, href),
        })

    return unique_items(data)


def _parse_api_scheme(item, category_hint):
    title = clean_text(item.get("title"))
    if not is_good_title(title, min_words=3):
        return None

    categories = item.get("schemeCategory") or []
    if isinstance(categories, str):
        categories = [categories]
    ministry = clean_text(item.get("ministry") or item.get("npiMinistry") or "National Portal of India")
    slug = clean_text(item.get("slug"))

    return {
        "title": title,
        "description": clean_text(item.get("description")),
        "ministry": ministry,
        "category": clean_text(", ".join(categories)) or category_hint or "India Portal",
        "url": absolute_url("https://www.myscheme.gov.in/", f"/schemes/{slug}" if slug else ""),
    }


def _scrape_india_api(url, max_pages=None):
    session = get_session(
        extra_headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.india.gov.in",
            "Referer": url,
        }
    )
    category = _category_from_url(url)
    data = []
    page_number = 1
    total = None

    while total is None or len(data) < total:
        if max_pages is not None and page_number > max_pages:
            break

        payload = {
            "categories": None,
            "mustFilter": [],
            "pageNumber": page_number,
            "pageSize": INDIA_PAGE_SIZE,
        }
        for attempt in range(1, 4):
            try:
                response = session.post(
                    INDIA_SEARCH_API_URL,
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt * 2)

        schemes_response = (response.json() or {}).get("schemesResponse") or {}
        total = int(schemes_response.get("total") or 0)
        results = schemes_response.get("results") or []

        for item in results:
            parsed = _parse_api_scheme(item, category)
            if parsed:
                data.append(parsed)

        print(f"INDIA scraped {len(results)} API items from page {page_number} ({len(data)} kept)")
        if not results:
            break
        page_number += 1

    return unique_items(data)


def scrape_india(url, max_pages=None):
    category = _category_from_url(url)

    try:
        data = _scrape_india_api(url, max_pages=max_pages)
        if data:
            print(f"INDIA scraped {len(data)} items from API for {url}")
            return data
    except Exception as exc:
        print(f"INDIA API fetch failed for {url}: {type(exc).__name__}: {exc}")

    try:
        soup = get_soup(url)
        page_text = clean_text(soup.get_text(" ", strip=True)).lower()
        if "no data found" not in page_text:
            data = _parse_featured_schemes(soup, url, category)
            if data:
                print(f"INDIA scraped {len(data)} items from {url}")
                return data
    except Exception as exc:
        print(f"INDIA primary fetch failed for {url}: {type(exc).__name__}: {exc}")

    fallback_soup = get_soup(INDIA_SCHEMES_URL)
    data = _parse_featured_schemes(fallback_soup, INDIA_SCHEMES_URL, category)
    print(f"INDIA scraped {len(data)} items from {url} via fallback")
    return data

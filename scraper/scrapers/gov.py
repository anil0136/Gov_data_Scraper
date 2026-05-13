import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, urlparse

from .common import absolute_url, clean_text, get_session, get_soup, get_with_retry, is_good_title, unique_items


GOV_BASE_URL = "https://services.india.gov.in"
GOV_CATEGORY_LISTING_PATH = "/category/listing"
GOV_SERVICE_LISTING_PATH = "/service/listing"


def _is_services_india_url(url):
    return urlparse(url).netloc == "services.india.gov.in"


def _is_category_listing_url(url):
    parsed = urlparse(url)
    return _is_services_india_url(url) and parsed.path == GOV_CATEGORY_LISTING_PATH


def _is_service_listing_url(url):
    parsed = urlparse(url)
    return _is_services_india_url(url) and parsed.path == GOV_SERVICE_LISTING_PATH


def _category_sort_key(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    cat_id = query.get("cat_id", [""])[0]
    try:
        return (0, int(cat_id))
    except ValueError:
        return (1, cat_id)


def _service_key(item):
    url = clean_text(item.get("url"))
    title = clean_text(item.get("title")).lower()
    if url:
        return url.lower()
    return title


def _page_number(url):
    query = parse_qs(urlparse(url).query)
    raw_page = query.get("page_no", ["1"])[0]
    try:
        return int(raw_page)
    except ValueError:
        return 1


def _discover_category_urls(soup, base_url):
    urls = set()
    selectors = (
        'a[href*="/service/listing?cat_id="]',
        'a[href*="/service/listing/?cat_id="]',
    )
    for selector in selectors:
        for link in soup.select(selector):
            href = absolute_url(base_url, link.get("href"))
            if _is_service_listing_url(href):
                urls.add(href)
    return sorted(urls, key=_category_sort_key)


def _discover_pagination_urls(soup, base_url):
    urls = set()
    for link in soup.select(".pagination a, ul.pagination a, .pager a"):
        href = link.get("href")
        if not href or href == "#":
            continue
        page_url = absolute_url(base_url, href)
        if _is_service_listing_url(page_url):
            urls.add(page_url)
    return sorted(urls, key=_page_number)


def _category_name(soup):
    heading = soup.select_one(".right-content h2, h2")
    if heading:
        return clean_text(heading.get_text(" ", strip=True))
    breadcrumb = soup.select("ul.breadcrumb li, .breadcrumb li, .breadcrumb a")
    if breadcrumb:
        return clean_text(breadcrumb[-1].get_text(" ", strip=True))
    return ""


def _parse_listing_items(soup, page_url, category=""):
    data = []

    for item in soup.select(".edu-lern-con"):
        title_link = item.select_one("h3 a")
        title = clean_text(title_link.get_text(" ", strip=True) if title_link else "")
        if not is_good_title(title):
            continue

        description = clean_text(
            item.select_one("p").get_text(" ", strip=True)
            if item.select_one("p")
            else ""
        )
        service_type = clean_text(
            item.select_one(".status_icon").get_text(" ", strip=True)
            if item.select_one(".status_icon")
            else ""
        )
        detail_link = item.select_one("a.more_det_btn") or title_link

        data.append({
            "title": title,
            "service_type": service_type,
            "description": description,
            "department": category,
            "url": absolute_url(page_url, detail_link.get("href") if detail_link else None),
        })

    return data


def _scrape_gov_category(category_url, max_pages=None):
    session = get_session()
    data_by_key = {}
    visited_pages = set()
    pending_pages = deque([category_url])
    category = ""

    while pending_pages:
        page_url = pending_pages.popleft()
        if page_url in visited_pages:
            continue
        if max_pages is not None and len(visited_pages) >= max_pages:
            print(f"GOV reached page limit ({max_pages}) before {page_url}")
            break

        try:
            response = get_with_retry(session, page_url, timeout=45, attempts=5, backoff=3)
        except Exception as exc:
            print(f"GOV skipped {page_url} after retries: {type(exc).__name__}: {exc}")
            visited_pages.add(page_url)
            continue

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        visited_pages.add(page_url)

        category = category or _category_name(soup)
        page_items = _parse_listing_items(soup, page_url, category=category)
        for item in page_items:
            data_by_key[_service_key(item)] = item

        for next_url in _discover_pagination_urls(soup, page_url):
            if next_url not in visited_pages:
                pending_pages.append(next_url)

        print(
            "GOV scraped "
            f"{len(page_items)} items from {page_url} "
            f"({len(data_by_key)} category unique total)"
        )

    return data_by_key, visited_pages


def scrape_gov(url, max_pages=None):
    start_soup = get_soup(url)

    if _is_category_listing_url(url):
        category_urls = _discover_category_urls(start_soup, url)
    else:
        category_urls = [url]

    data_by_key = {}
    visited_pages = set()

    if max_pages is None and len(category_urls) > 1:
        workers = int(os.environ.get("GOVSCRAPER_GOV_WORKERS", "5"))
        print(f"GOV scraping {len(category_urls)} categories with {workers} workers...")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_scrape_gov_category, category_url): category_url
                for category_url in category_urls
            }
            for future in as_completed(futures):
                try:
                    category_data, category_pages = future.result()
                except Exception as exc:
                    print(
                        "GOV category failed after retries "
                        f"{futures[future]}: {type(exc).__name__}: {exc}"
                    )
                    continue
                data_by_key.update(category_data)
                visited_pages.update(category_pages)
                print(
                    "GOV category completed "
                    f"{futures[future]}: {len(category_pages)} pages, "
                    f"{len(category_data)} unique items"
                )
    else:
        processed_pages = 0
        for category_url in category_urls:
            category_data, category_pages = _scrape_gov_category(
                category_url,
                None if max_pages is None else max_pages - processed_pages,
            )
            data_by_key.update(category_data)
            visited_pages.update(category_pages)
            processed_pages += len(category_pages)
            if max_pages is not None and processed_pages >= max_pages:
                break

    data = list(data_by_key.values())
    print(
        f"GOV finished {len(visited_pages)} pages across "
        f"{len(category_urls)} categories with {len(data)} unique items."
    )
    return unique_items(data)

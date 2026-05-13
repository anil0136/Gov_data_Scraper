from collections import deque
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .common import absolute_url, clean_text, get_soup, is_good_title, unique_items


STARTUP_GRANTS_MAX_PAGES = 100
GRANTSETU_MAX_PAGES = 50


def _url_with_page(url, page_number):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_number)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _same_host_url(base_url, href):
    full_url = absolute_url(base_url, href)
    return urlparse(full_url).netloc == urlparse(base_url).netloc


def _discover_grantsetu_urls(soup, base_url):
    urls = {base_url}
    for link in soup.select('a[href^="/grants?agency="], a[href*="/grants?agency="], a[href*="page="]'):
        href = link.get("href")
        if href and _same_host_url(base_url, href):
            urls.add(absolute_url(base_url, href))
    return [base_url] + sorted(url for url in urls if url != base_url)


def _parse_grantsetu_page(soup, url):
    data = []

    for item in soup.select("article.card"):
        title_tag = item.select_one("h3")
        title = clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")
        if not is_good_title(title):
            continue

        lines = [
            clean_text(line)
            for line in item.get_text("\n", strip=True).split("\n")
            if clean_text(line)
        ]
        organization = lines[0] if lines else ""
        title_index = lines.index(title) if title in lines else -1
        description = lines[title_index + 1] if title_index >= 0 and title_index + 1 < len(lines) else ""
        amount = lines[title_index + 2] if title_index >= 0 and title_index + 2 < len(lines) else ""
        link = item.select_one('a[href*="/grants/"]') or item.select_one("a[href]")

        data.append({
            "title": title,
            "organization": organization,
            "description": description,
            "funding_amount": amount,
            "url": absolute_url(url, link.get("href") if link else None),
        })

    return data


def _parse_startupgrantsindia_page(soup, url):
    data = []

    for title_tag in soup.select("h2"):
        title = clean_text(title_tag.get_text(" ", strip=True))
        if not is_good_title(title):
            continue

        card = title_tag.find_parent(["article", "div"])
        lines = [
            clean_text(line)
            for line in (card.get_text("\n", strip=True).split("\n") if card else [])
            if clean_text(line)
        ]
        description = next((line for line in lines if line != title and len(line) > 40), "")
        amount = next((line for line in lines if "\u20b9" in line or "$" in line or "grant" in line.lower()), "")
        link = title_tag.find_parent("a") or (card.select_one("a[href]") if card else None)

        data.append({
            "title": title,
            "organization": "Startup Grants India",
            "description": description,
            "funding_amount": amount,
            "url": absolute_url(url, link.get("href") if link else None),
        })

    return data


def _get_soup_with_retry(url, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            return get_soup(url, timeout=60)
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt * 2)


def scrape_grants(url, max_pages=None):
    data = []

    if "grantsetu.in" in url:
        first_soup = _get_soup_with_retry(url)
        pending = deque(_discover_grantsetu_urls(first_soup, url))
        visited = set()
        page_limit = max_pages or GRANTSETU_MAX_PAGES

        while pending and len(visited) < page_limit:
            page_url = pending.popleft()
            if page_url in visited:
                continue
            try:
                soup = first_soup if page_url == url else _get_soup_with_retry(page_url)
            except Exception as exc:
                print(f"GRANTSETU skipped {page_url}: {type(exc).__name__}: {exc}")
                continue
            visited.add(page_url)
            page_items = _parse_grantsetu_page(soup, page_url)
            data.extend(page_items)
            print(f"GRANTSETU scraped {len(page_items)} items from {page_url}")

            for next_url in _discover_grantsetu_urls(soup, page_url):
                if next_url not in visited:
                    pending.append(next_url)
    elif "startupgrantsindia.com" in url:
        page_limit = max_pages or STARTUP_GRANTS_MAX_PAGES
        seen_titles = set()
        for page_number in range(1, page_limit + 1):
            page_url = _url_with_page(url, page_number)
            try:
                soup = _get_soup_with_retry(page_url)
            except Exception as exc:
                print(f"STARTUPGRANTSINDIA stopped at {page_url}: {type(exc).__name__}: {exc}")
                break
            page_items = _parse_startupgrantsindia_page(soup, page_url)
            new_items = []
            for item in page_items:
                key = clean_text(item.get("title")).lower()
                if key and key not in seen_titles:
                    seen_titles.add(key)
                    new_items.append(item)
            data.extend(new_items)
            print(f"STARTUPGRANTSINDIA scraped {len(new_items)} new items from {page_url}")
            if not page_items or not new_items:
                break
    elif "startupindia.gov.in" in url:
        soup = _get_soup_with_retry(url)
        for link in soup.select(".scroll-simple .inner a[href]"):
            title = clean_text(link.get_text(" ", strip=True))
            lowered = title.lower()
            if not is_good_title(title) or not any(
                word in lowered for word in ("scheme", "startup", "grant", "fund", "mission")
            ):
                continue

            data.append({
                "title": title,
                "organization": "Startup India",
                "description": "",
                "funding_amount": "",
                "url": absolute_url(url, link.get("href")),
            })

    print(f"GRANTS scraped {len(data)} items from {url}")
    return unique_items(data)

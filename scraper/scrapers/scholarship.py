import re
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .common import absolute_url, clean_text, get_session, get_soup, is_good_title, unique_items


BUDDY4STUDY_APP_CHUNK_RE = r"/_next/static/chunks/pages/_app-[^\" ]+\.js"
BUDDY4STUDY_API_BASE = "https://api.buddy4study.com/api/v1.0/ssms"
WEMAKESCHOLARS_MAX_PAGES = 100


def _first_text(parent, selector):
    node = parent.select_one(selector)
    return clean_text(node.get_text(" ", strip=True) if node else "")


def _parse_wemakescholars_cards(soup, base_url):
    data = []

    for card in soup.select("div.post.featured_post, div.post"):
        title_link = card.select_one("h2.post-title a")
        title = clean_text(title_link.get_text(" ", strip=True) if title_link else "")
        if not is_good_title(title):
            continue

        logo = card.select_one("img.internship-col-img")
        provider = _first_text(card, ".uni-btn")
        deadline = ""
        amount = ""

        for block in card.select(".text-line-div, .row .text-line-div"):
            label = _first_text(block, "p.text-line").rstrip(":").lower()
            value = ""
            spans = [clean_text(node.get_text(" ", strip=True)) for node in block.select("span")]
            spans = [item for item in spans if item]
            if spans:
                value = spans[-1]

            if label == "deadline":
                deadline = value
            elif label == "funding type":
                amount = value
            elif label == "scholarship can be taken at" and value:
                provider = value

        data.append({
            "title": title,
            "provider": provider or "WeMakeScholars",
            "deadline": deadline,
            "amount": amount,
            "url": absolute_url(base_url, title_link.get("href") if title_link else None),
            "image_url": absolute_url(base_url, logo.get("src") if logo else None),
        })

    return data


def _extract_buddy4study_token(session):
    page = session.get("https://www.buddy4study.com/scholarships", timeout=30)
    page.raise_for_status()
    match = re.search(BUDDY4STUDY_APP_CHUNK_RE, page.text)
    if not match:
        raise ValueError("Unable to locate Buddy4Study app bundle.")

    app_chunk = absolute_url("https://www.buddy4study.com/", match.group(0))
    response = session.get(app_chunk, timeout=30)
    response.raise_for_status()
    match = re.search(r"eyJhbGciOiJIUzI1Ni[A-Za-z0-9._-]+", response.text)
    if not match:
        raise ValueError("Unable to locate Buddy4Study API token in app bundle.")
    return match.group(0)


def _parse_buddy4study_items(items):
    data = []

    for item in items:
        multilingual = (item.get("scholarshipMultilinguals") or [{}])[0]
        title = clean_text(
            multilingual.get("title")
            or item.get("scholarshipName")
            or item.get("title")
        )
        if not is_good_title(title):
            continue

        data.append({
            "title": title,
            "provider": "Buddy4Study",
            "deadline": clean_text(item.get("deadlineDate") or item.get("publishDate")),
            "amount": clean_text(multilingual.get("purposeAward") or item.get("purposeAward") or ""),
            "url": absolute_url("https://www.buddy4study.com/", item.get("pageSlug") or f"scholarship/{item.get('slug', '')}"),
            "image_url": clean_text(item.get("logoFid") or item.get("logo") or ""),
        })

    return data


def _scrape_buddy4study(url):
    session = get_session()
    token = _extract_buddy4study_token(session)
    headers = {"Authorization": f"Bearer {token}"}

    featured_response = session.get(
        f"{BUDDY4STUDY_API_BASE}/scholarship/featured",
        headers=headers,
        timeout=30,
    )
    featured_response.raise_for_status()

    recent_response = session.get(
        f"{BUDDY4STUDY_API_BASE}/scholarshipResult",
        headers=headers,
        timeout=30,
    )
    recent_response.raise_for_status()

    recent_payload = recent_response.json()
    recent_items = recent_payload.get("data", []) if isinstance(recent_payload, dict) else []
    featured_items = featured_response.json() if isinstance(featured_response.json(), list) else []

    data = _parse_buddy4study_items(featured_items)
    data.extend(_parse_buddy4study_items(recent_items))
    return data


def _url_with_page(url, page_number):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_number)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _scrape_wemakescholars(url, max_pages=None):
    data = []
    seen_pages = set()
    seen_titles = set()
    page_number = 1
    page_limit = max_pages or WEMAKESCHOLARS_MAX_PAGES

    while page_number <= page_limit:
        page_url = _url_with_page(url, page_number)
        if page_url in seen_pages:
            break
        seen_pages.add(page_url)

        try:
            soup = get_soup(page_url, timeout=60)
        except Exception as exc:
            print(f"WEMAKESCHOLARS stopped at {page_url}: {type(exc).__name__}: {exc}")
            break
        page_items = _parse_wemakescholars_cards(soup, page_url)
        new_items = []
        for item in page_items:
            key = clean_text(item.get("title")).lower()
            if key and key not in seen_titles:
                seen_titles.add(key)
                new_items.append(item)

        data.extend(new_items)
        print(f"WEMAKESCHOLARS scraped {len(new_items)} new items from {page_url}")

        if not page_items or not new_items:
            break
        time.sleep(0.3)
        page_number += 1

    return data


def scrape_scholarship(url, max_pages=None):
    if "buddy4study.com" in url:
        data = _scrape_buddy4study(url)
    else:
        data = _scrape_wemakescholars(url, max_pages=max_pages)

    print(f"SCHOLARSHIP scraped {len(data)} items from {url}")
    return unique_items(data)

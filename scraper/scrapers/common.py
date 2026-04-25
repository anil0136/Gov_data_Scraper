from urllib.parse import urljoin

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


BAD_TITLE_PARTS = (
    "translationdisclaimer",
    "translations of the content",
    "you need to enable javascript",
    "about startupgrantsindia",
    "filters",
    "menu",
    "login",
    "dashboard",
    "no data found",
)


def clean_text(value):
    return " ".join((value or "").split())


def is_good_title(title, min_words=2):
    title = clean_text(title)
    lowered = title.lower()
    if not title or len(title) < 8:
        return False
    if any(part in lowered for part in BAD_TITLE_PARTS):
        return False
    return len(title.split()) >= min_words


def absolute_url(base_url, href):
    if not href:
        return base_url
    return urljoin(base_url, href)


def get_session(extra_headers=None):
    session = requests.Session()
    session.trust_env = False
    session.headers.update(DEFAULT_HEADERS)
    if extra_headers:
        session.headers.update(extra_headers)
    return session


def get_soup(url, parser="html.parser", timeout=30, extra_headers=None):
    session = get_session(extra_headers=extra_headers)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    from bs4 import BeautifulSoup

    return BeautifulSoup(response.text, parser)


def unique_items(items):
    seen = set()
    unique = []
    for item in items:
        title = clean_text(item.get("title"))
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        item["title"] = title
        seen.add(key)
        unique.append(item)
    return unique

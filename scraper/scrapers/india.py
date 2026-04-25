from urllib.parse import parse_qs, urlparse

from .common import absolute_url, clean_text, get_soup, is_good_title, unique_items


INDIA_SCHEMES_URL = "https://www.india.gov.in/my-government/schemes?page=1"


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


def scrape_india(url):
    category = _category_from_url(url)

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

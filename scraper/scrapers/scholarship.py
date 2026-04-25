import re

from .common import absolute_url, clean_text, get_session, get_soup, is_good_title, unique_items


BUDDY4STUDY_APP_CHUNK = "https://www.buddy4study.com/_next/static/chunks/pages/_app-f0372416c99b0add.js"
BUDDY4STUDY_API_BASE = "https://api.buddy4study.com/api/v1.0/ssms"


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
    response = session.get(BUDDY4STUDY_APP_CHUNK, timeout=30)
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


def scrape_scholarship(url):
    if "buddy4study.com" in url:
        data = _scrape_buddy4study(url)
    else:
        soup = get_soup(url)
        data = _parse_wemakescholars_cards(soup, url)

    print(f"SCHOLARSHIP scraped {len(data)} items from {url}")
    return unique_items(data)

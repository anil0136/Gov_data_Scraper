import json
import re

from bs4 import BeautifulSoup

from .common import absolute_url, clean_text, get_session, get_soup, is_good_title, unique_items


TENDERS_ON_TIME_API_URL = "https://www.tendersontime.com/ApiTenders/getfilterTender"
TENDERS_ON_TIME_SEARCH_KEYWORD = "tender"
TENDERKART_HEADERS = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}
DEFAULT_TENDER_LIMIT = 20


def _iso_to_date(value):
    value = clean_text(value)
    if "T" in value:
        return value.split("T", 1)[0]
    return value


def _summary_to_text(value):
    return clean_text(BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True))


def _extract_tot_category(summary):
    match = re.search(r"Tender Category\s+(.+)$", summary, re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""


def _parse_tendersontime_results(payload, source_url):
    rows = []

    for item in payload.get("searchdata", []):
        summary = _summary_to_text(item.get("Tender_Summery"))
        title = clean_text(summary)
        if not is_good_title(title):
            continue

        rows.append({
            "source": "TendersOnTime",
            "external_id": clean_text(str(item.get("id", ""))),
            "title": title,
            "organization": "",
            "location": "",
            "state": "",
            "country": clean_text(item.get("Country_Name_Known")),
            "status": "Active",
            "procurement_type": "",
            "category": _extract_tot_category(summary),
            "tender_value": clean_text(item.get("Tender_Value")),
            "published_on": _iso_to_date(item.get("Posting_Date")),
            "deadline": _iso_to_date(item.get("Bid_Deadline_1")),
            "description": summary,
            "source_url": source_url,
            "url": clean_text(item.get("Tender_url")) or source_url,
            "raw_data": item,
        })

    return rows


def _pick_first_texts(parent, selectors):
    values = []
    for selector in selectors:
        for node in parent.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                values.append(text)
    return values


def _parse_tenderkart_cards(soup, source_url):
    rows = []

    for card in soup.select('div[aria-label^="Open tender:"]'):
        organization_tag = card.select_one("h3 a[href]") or card.select_one("h3")
        organization = clean_text(organization_tag.get_text(" ", strip=True) if organization_tag else "")

        title_tag = card.select_one("p")
        title = clean_text(title_tag.get_text(" ", strip=True) if title_tag else "")
        if not title:
            aria_label = clean_text(card.get("aria-label", ""))
            title = clean_text(aria_label.replace("Open tender:", "", 1))
        if not is_good_title(title):
            continue

        link = organization_tag.get("href") if organization_tag and organization_tag.has_attr("href") else ""
        info_parts = _pick_first_texts(card, ["div.flex.flex-wrap.items-center.gap-x-3.gap-y-1 span"])
        location = info_parts[0] if info_parts else ""
        published_on = next((part.replace("Last activity", "").strip() for part in info_parts if "Last activity" in part), "")

        badge_texts = []
        for container in card.find_all("div"):
            child_texts = []
            for child in container.find_all(recursive=False):
                text = clean_text(child.get_text(" ", strip=True))
                if not text or len(text) > 40:
                    continue
                lowered = text.lower()
                if text in {organization, title, location, published_on}:
                    continue
                if "last activity" in lowered or "awarded bids" in lowered or text in {"Save", "Share"}:
                    continue
                child_texts.append(text)
            if len(child_texts) >= 3:
                badge_texts = child_texts
                break

        state = badge_texts[0] if len(badge_texts) > 0 else ""
        status = badge_texts[1] if len(badge_texts) > 1 else ""
        procurement_type = badge_texts[2] if len(badge_texts) > 2 else ""
        category = badge_texts[3] if len(badge_texts) > 3 else ""

        card_text = clean_text(card.get_text(" | ", strip=True))
        value_match = re.search(r"(\d[\d.,]*\s*(?:Cr|Crore|Lakh|Lakhs|Thousand|Million|Billion))", card_text, re.IGNORECASE)
        tender_value = clean_text(value_match.group(1)) if value_match else ""

        rows.append({
            "source": "TenderKart",
            "external_id": clean_text(link.rsplit("/", 1)[-1]),
            "title": title,
            "organization": organization,
            "location": location,
            "state": state,
            "country": "India",
            "status": status,
            "procurement_type": procurement_type,
            "category": category,
            "tender_value": tender_value,
            "published_on": published_on,
            "deadline": "",
            "description": title,
            "source_url": source_url,
            "url": absolute_url(source_url, link),
            "raw_data": {},
        })

    return rows


def scrape_tendersontime(url, limit=DEFAULT_TENDER_LIMIT):
    session = get_session()
    response = session.post(
        TENDERS_ON_TIME_API_URL,
        data={
            "searchType": "1",
            "mainsearch": "",
            "tendersaction": "FilterTenders",
            "status": "1",
            "keyword": TENDERS_ON_TIME_SEARCH_KEYWORD,
            "pageNo": "1",
            "orderby": "Posting_Date DESC",
            "perPageRecord": str(limit),
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = json.loads(response.text.strip())
    data = _parse_tendersontime_results(payload, url)
    print(f"TENDERSONTIME scraped {len(data)} items from {url}")
    return data


def scrape_tenderkart(url):
    soup = get_soup(url, extra_headers=TENDERKART_HEADERS)
    data = _parse_tenderkart_cards(soup, url)
    print(f"TENDERKART scraped {len(data)} items from {url}")
    return data


def scrape_tenders(source_name, url, limit=DEFAULT_TENDER_LIMIT):
    source_name = (source_name or "").strip().lower()
    if source_name == "tendersontime":
        return unique_items(scrape_tendersontime(url, limit=limit))
    if source_name == "tenderkart":
        return unique_items(scrape_tenderkart(url))
    raise ValueError(f"Unsupported tender source: {source_name}")

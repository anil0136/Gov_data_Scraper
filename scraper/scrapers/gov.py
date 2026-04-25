from .common import absolute_url, clean_text, get_soup, is_good_title, unique_items

def scrape_gov(url):
    soup = get_soup(url)
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
            "url": absolute_url(url, detail_link.get("href") if detail_link else None),
        })

    print(f"GOV scraped {len(data)} items from {url}")
    return unique_items(data)

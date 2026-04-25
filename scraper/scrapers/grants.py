from .common import absolute_url, clean_text, get_soup, is_good_title, unique_items


def scrape_grants(url):
    soup = get_soup(url)
    data = []

    if "grantsetu.in" in url:
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
            link = item.select_one("a[href]")

            data.append({
                "title": title,
                "organization": organization,
                "description": description,
                "funding_amount": amount,
                "url": absolute_url(url, link.get("href") if link else None),
            })
    elif "startupgrantsindia.com" in url:
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
    elif "startupindia.gov.in" in url:
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

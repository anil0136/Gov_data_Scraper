import time
from urllib.parse import unquote, urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .common import absolute_url, clean_text, get_session, is_good_title, unique_items
from .driver import get_driver


MYSCHEME_API_URL = "https://api.myscheme.gov.in/search/v6/schemes"
MYSCHEME_DETAIL_API_URL = "https://api.myscheme.gov.in/schemes/v6/public/schemes"
MYSCHEME_API_KEY = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"
MYSCHEME_PAGE_SIZE = 100
MYSCHEME_DETAIL_DELAY_SECONDS = 0.35
MYSCHEME_DETAIL_RETRIES = 5


def _category_from_url(url):
    path = unquote(urlparse(url).path)
    marker = "/search/category/"
    if marker in path:
        return clean_text(path.split(marker, 1)[1])
    return "MyScheme"


def _label(value):
    if isinstance(value, dict):
        return clean_text(value.get("label") or value.get("name") or value.get("value") or "")
    return clean_text(value)


def _labels(value):
    if isinstance(value, list):
        return [label for label in (_label(item) for item in value) if label]
    label = _label(value)
    return [label] if label else []


def _rich_text_inline(children):
    parts = []
    for child in children or []:
        if isinstance(child, dict):
            if "text" in child:
                parts.append(child.get("text") or "")
            else:
                parts.append(_rich_text_inline(child.get("children") or []))
        elif child:
            parts.append(str(child))
    return clean_text(" ".join(part for part in parts if part is not None))


def _rich_text_lines(nodes, indent=0):
    lines = []
    if isinstance(nodes, dict):
        nodes = [nodes]

    for node in nodes or []:
        if isinstance(node, str):
            text = clean_text(node)
            if text:
                lines.append(text)
            continue
        if not isinstance(node, dict):
            continue

        node_type = node.get("type")
        children = node.get("children") or []

        if "text" in node:
            text = clean_text(node.get("text"))
            if text:
                lines.append(text)
        elif node_type == "paragraph":
            text = _rich_text_inline(children)
            if text:
                lines.append(text)
        elif node_type == "list_item":
            text = _rich_text_inline(children)
            nested = _rich_text_lines([child for child in children if isinstance(child, dict) and "text" not in child], indent + 1)
            if text:
                lines.append(f"{'  ' * indent}- {text}")
            lines.extend(nested)
        elif node_type in {"ol_list", "ul_list"}:
            for index, child in enumerate(children, 1):
                text = _rich_text_inline(child.get("children") or []) if isinstance(child, dict) else clean_text(child)
                nested = _rich_text_lines(
                    [grandchild for grandchild in (child.get("children") or []) if isinstance(grandchild, dict) and "text" not in grandchild],
                    indent + 1,
                ) if isinstance(child, dict) else []
                if text:
                    prefix = f"{index}." if node_type == "ol_list" else "-"
                    lines.append(f"{'  ' * indent}{prefix} {text}")
                lines.extend(nested)
        elif node_type in {"table", "table_body"}:
            lines.extend(_rich_text_lines(children, indent))
        elif node_type == "table_row":
            cells = []
            for cell in children:
                cell_text = _rich_text_inline(cell.get("children") or []) if isinstance(cell, dict) else clean_text(cell)
                if cell_text:
                    cells.append(cell_text)
            if cells:
                lines.append(" | ".join(cells))
        else:
            text = _rich_text_inline(children)
            if text:
                lines.append(text)
            lines.extend(_rich_text_lines([child for child in children if isinstance(child, dict) and "text" not in child], indent))

    return lines


def _rich_text(value):
    if not value:
        return ""
    if isinstance(value, str):
        return clean_text(value)
    return "\n".join(line for line in _rich_text_lines(value) if line)


def _section(title, body):
    if not body:
        return ""
    text = body.strip() if isinstance(body, str) else _rich_text(body)
    return f"{title}\n{text}" if text else ""


def _references_text(references):
    lines = []
    for reference in references or []:
        if not isinstance(reference, dict):
            continue
        title = clean_text(reference.get("title") or "Reference")
        url = clean_text(reference.get("url"))
        if title and url:
            lines.append(f"{title}: {url}")
        elif title:
            lines.append(title)
        elif url:
            lines.append(url)
    return "\n".join(lines)


def _application_process_text(processes):
    lines = []
    for process in processes or []:
        if not isinstance(process, dict):
            continue
        mode = clean_text(process.get("mode"))
        url = clean_text(process.get("url"))
        heading = "Application Process"
        if mode:
            heading = f"{heading} ({mode})"
        body = _rich_text(process.get("process"))
        if url:
            body = f"{body}\nApply URL: {url}" if body else f"Apply URL: {url}"
        if body:
            lines.append(f"{heading}\n{body}")
    return "\n\n".join(lines)


def _definitions_text(definitions):
    lines = []
    for definition in definitions or []:
        if not isinstance(definition, dict):
            continue
        name = clean_text(definition.get("name") or "Definition")
        body = _rich_text(definition.get("definition"))
        source = clean_text(definition.get("source"))
        if source:
            body = f"{body}\nSource: {source}" if body else f"Source: {source}"
        if body:
            lines.append(f"{name}\n{body}")
    return "\n\n".join(lines)


def _documents_text(data):
    documents = data.get("documents") or data.get("documentsRequired") or data.get("requiredDocuments")
    if isinstance(documents, dict):
        documents = documents.get("documents") or documents.get("list") or documents.get("description")
    return _rich_text(documents)


def _fetch_detail(session, slug):
    if not slug:
        return None

    last_error = None
    for attempt in range(1, MYSCHEME_DETAIL_RETRIES + 1):
        try:
            response = session.get(
                MYSCHEME_DETAIL_API_URL,
                params={"slug": slug, "lang": "en"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if int(payload.get("statusCode") or 0) != 200:
                last_error = f"statusCode={payload.get('statusCode')}"
            else:
                data = payload.get("data") or {}
                detail = data.get("en") or data
                if detail:
                    return detail
                last_error = "empty detail payload"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        wait_seconds = 3 * attempt if "429" in str(last_error) else 0.75 * attempt
        time.sleep(wait_seconds)

    raise RuntimeError(f"Could not fetch myScheme detail for {slug}: {last_error}")


def _parse_api_item(item, category_hint=""):
    fields = item.get("fields") or item
    title = clean_text(fields.get("schemeName") or fields.get("title"))
    if not is_good_title(title):
        return None

    categories = _labels(fields.get("schemeCategory"))
    category = clean_text(", ".join(categories)) or category_hint or "MyScheme"
    ministry = clean_text(fields.get("nodalMinistryName") or fields.get("ministry") or "")
    description = clean_text(fields.get("briefDescription") or fields.get("description") or "")
    slug = clean_text(fields.get("slug") or item.get("slug"))

    return {
        "title": title,
        "description": description,
        "eligibility": "",
        "benefits": ministry,
        "category": category,
        "ministry": ministry,
        "department": "",
        "level": clean_text(fields.get("level") or ""),
        "tags": clean_text(", ".join(fields.get("tags") or [])),
        "application_process": "",
        "documents": "",
        "references": "",
        "raw_data": {},
        "url": absolute_url("https://www.myscheme.gov.in/", f"/schemes/{slug}" if slug else ""),
        "_slug": slug,
    }


def _merge_detail(parsed, detail):
    if not detail:
        parsed.pop("_slug", None)
        return parsed

    basic = detail.get("basicDetails") or {}
    content = detail.get("schemeContent") or {}
    eligibility = detail.get("eligibilityCriteria") or {}
    application_process = detail.get("applicationProcess") or []
    definitions = detail.get("schemeDefinitions") or []

    title = clean_text(basic.get("schemeName") or parsed["title"])
    categories = _labels(basic.get("schemeCategory"))
    ministry = _label(basic.get("nodalMinistryName")) or parsed.get("ministry", "")
    department = _label(basic.get("nodalDepartmentName"))
    level = _label(basic.get("level")) or parsed.get("level", "")
    tags = basic.get("tags") or []

    brief = clean_text(content.get("briefDescription") or parsed.get("description") or "")
    details = content.get("detailedDescription_md") or _rich_text(content.get("detailedDescription"))
    exclusions = content.get("exclusions_md") or _rich_text(content.get("exclusions"))
    definitions_text = _definitions_text(definitions)
    references = _references_text(content.get("references"))
    documents = _documents_text(detail)
    application_text = _application_process_text(application_process)

    description_sections = [
        _section("Brief Description", brief),
        _section("Details", details),
        _section("Exclusions", exclusions),
        _section("Definitions", definitions_text),
    ]

    benefit_type = _label(content.get("benefitTypes"))
    benefits = content.get("benefits_md") or _rich_text(content.get("benefits"))
    if benefit_type:
        benefits = f"Benefit Type: {benefit_type}\n{benefits}" if benefits else f"Benefit Type: {benefit_type}"

    eligibility_text = clean_text(eligibility.get("eligibilityDescription_md") or "")
    if not eligibility_text:
        eligibility_text = _rich_text(eligibility.get("eligibilityDescription"))

    parsed.update({
        "title": title,
        "description": "\n\n".join(section for section in description_sections if section),
        "eligibility": eligibility_text,
        "benefits": benefits,
        "category": clean_text(", ".join(categories)) or parsed.get("category") or "MyScheme",
        "ministry": ministry,
        "department": department,
        "level": level,
        "tags": clean_text(", ".join(tags)),
        "application_process": application_text,
        "documents": documents,
        "references": references,
        "raw_data": detail,
    })
    parsed.pop("_slug", None)
    return parsed


def _scrape_myscheme_api(url, max_pages=None):
    session = get_session(
        extra_headers={
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.myscheme.gov.in",
            "Referer": "https://www.myscheme.gov.in/",
            "x-api-key": MYSCHEME_API_KEY,
        }
    )
    category_hint = _category_from_url(url)
    data = []
    offset = 0
    page_count = 0
    total = None

    while total is None or offset < total:
        if max_pages is not None and page_count >= max_pages:
            break

        response = session.get(
            MYSCHEME_API_URL,
            params={
                "lang": "en",
                "q": "",
                "keyword": "",
                "sort": "",
                "from": offset,
                "size": MYSCHEME_PAGE_SIZE,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        hits = ((payload.get("data") or {}).get("hits") or {})
        page = hits.get("page") or {}
        total = int(page.get("total") or 0)
        items = hits.get("items") or []
        page_count += 1

        for item in items:
            parsed = _parse_api_item(item, category_hint=category_hint)
            if parsed:
                slug = parsed.get("_slug")
                if slug:
                    try:
                        detail = _fetch_detail(session, slug)
                        parsed = _merge_detail(parsed, detail)
                        if MYSCHEME_DETAIL_DELAY_SECONDS:
                            time.sleep(MYSCHEME_DETAIL_DELAY_SECONDS)
                    except Exception as exc:
                        print(f"MYSCHEME detail failed for {slug}: {type(exc).__name__}: {exc}")
                        parsed.pop("_slug", None)
                else:
                    parsed.pop("_slug", None)
                data.append(parsed)

        print(f"MYSCHEME scraped {len(items)} API items from offset {offset} ({len(data)} kept)")
        if not items:
            break
        offset += MYSCHEME_PAGE_SIZE

    return unique_items(data)


def _scrape_myscheme_browser(url):
    data = []
    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        wait = WebDriverWait(driver, 25)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, '[role="article"][aria-labelledby^="scheme-name"]'))

        cards = driver.find_elements(By.CSS_SELECTOR, '[role="article"][aria-labelledby^="scheme-name"]')
        for card in cards:
            try:
                title_link = card.find_element(By.CSS_SELECTOR, 'h2[id^="scheme-name"] a')
                title = clean_text(title_link.text)
                if not is_good_title(title):
                    continue

                lines = [clean_text(line) for line in card.text.splitlines() if clean_text(line)]
                ministry = lines[1] if len(lines) > 1 else ""
                description = lines[2] if len(lines) > 2 else ""
                href = title_link.get_attribute("href")

                data.append({
                    "title": title,
                    "description": description,
                    "eligibility": "",
                    "benefits": "",
                    "category": "MyScheme",
                    "url": absolute_url(url, href),
                })
            except Exception:
                pass
    except TimeoutException:
        print(f"MYSCHEME timeout waiting for scheme cards on {url}")
    except WebDriverException as exc:
        print(f"MYSCHEME browser unavailable: {exc}")
    except Exception as exc:
        print(f"MYSCHEME exception: {type(exc).__name__}: {exc}")
    finally:
        if driver:
            driver.quit()

    print(f"MYSCHEME scraped {len(data)} items from {url}")
    return unique_items(data)


def scrape_myscheme(url, max_pages=None):
    try:
        data = _scrape_myscheme_api(url, max_pages=max_pages)
        print(f"MYSCHEME scraped {len(data)} items from API for {url}")
        return data
    except Exception as exc:
        print(f"MYSCHEME API failed for {url}: {type(exc).__name__}: {exc}")
        return _scrape_myscheme_browser(url)

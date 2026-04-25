# umang.py
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from .driver import get_driver
import requests
from bs4 import BeautifulSoup

_browser_unavailable = False


def _http_fallback(url):
    print(f"HTTP fallback skipped for UMANG SPA: Returning empty list for {url}")
    return []


def scrape_umang(url):
    global _browser_unavailable

    data = []
    driver = None
    try:
        if _browser_unavailable:
            print("UMANG browser unavailable, using HTTP fallback.")
            data = _http_fallback(url)
            print(f"UMANG scraped {len(data)} items from {url}")
            return data

        driver = get_driver()
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".scheme-name"))

        cards = driver.find_elements(By.CSS_SELECTOR, "div.list.ng-star-inserted")
        for card in cards:
            try:
                title = card.find_element(By.CSS_SELECTOR, ".scheme-name").text.strip()
                lines = [
                    line.strip()
                    for line in card.text.splitlines()
                    if line.strip()
                ]
                description = ""
                if title in lines:
                    title_index = lines.index(title)
                    if title_index + 1 < len(lines):
                        description = lines[title_index + 1]
                if title:
                    data.append({
                        "title": title,
                        "description": description,
                        "category": "UMANG",
                        "url": url
                    })
            except Exception:
                pass
    except TimeoutException:
        print(f"UMANG timeout waiting for scheme cards on {url}")
        print("Falling back to HTTP scraping...")
        data = _http_fallback(url)
    except WebDriverException as exc:
        _browser_unavailable = True
        print(f"UMANG browser unavailable: {exc}")
        print("Falling back to HTTP scraping...")
        data = _http_fallback(url)
    except Exception as exc:
        print(f"UMANG exception: {type(exc).__name__}: {exc}")
        print("Falling back to HTTP scraping...")
        data = _http_fallback(url)
    finally:
        if driver:
            driver.quit()

    print(f"UMANG scraped {len(data)} items from {url}")
    return data

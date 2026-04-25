from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .common import absolute_url, clean_text, is_good_title, unique_items
from .driver import get_driver


def scrape_myscheme(url):
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

from .config.urls import *

from .scrapers.umang import scrape_umang
from .scrapers.gov import scrape_gov
from .scrapers.myscheme import scrape_myscheme
from .scrapers.india import scrape_india
from .scrapers.scholarship import scrape_scholarship
from .scrapers.grants import scrape_grants
from .scrapers.tenders import scrape_tenders

from .services import *


def _save_scraped_data(label, data, save_function):
    print(f"    {label} scraping successful. Starting to store data into MongoDB...")
    save_function(data)
    print(f"    {label} data saved successfully to MongoDB.")


def run_all_scrapers(progress_callback=None):
    total_urls = len(UMANG_URLS) + len(GOV_URLS) + len(MYSCHEME_URLS) + len(INDIA_URLS) + len(SCHOLARSHIP_URLS) + len(GRANT_URLS) + len(TENDER_URLS)
    processed = 0

    print(f"Starting scraping of {total_urls} URLs...")
    if progress_callback:
        progress_callback(processed=processed, total=total_urls, source="", url="")

    # 🅰️ UMANG
    print(f"Processing UMANG ({len(UMANG_URLS)} URLs)...")
    for i, url in enumerate(UMANG_URLS, 1):
        print(f"  UMANG {i}/{len(UMANG_URLS)}: {url}")
        data = scrape_umang(url)
        _save_scraped_data("UMANG", data, save_umang)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="UMANG", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # 🅱️ GOV
    print(f"Processing GOV ({len(GOV_URLS)} URLs)...")
    for i, url in enumerate(GOV_URLS, 1):
        print(f"  GOV {i}/{len(GOV_URLS)}: {url}")
        data = scrape_gov(url)
        _save_scraped_data("GOV", data, save_gov)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="GOV", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # 🅲 MYSCHEME
    print(f"Processing MYSCHEME ({len(MYSCHEME_URLS)} URLs)...")
    for i, url in enumerate(MYSCHEME_URLS, 1):
        print(f"  MYSCHEME {i}/{len(MYSCHEME_URLS)}: {url}")
        data = scrape_myscheme(url)
        _save_scraped_data("MYSCHEME", data, save_myscheme)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="MYSCHEME", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # 🅳 INDIA
    print(f"Processing INDIA ({len(INDIA_URLS)} URLs)...")
    for i, url in enumerate(INDIA_URLS, 1):
        print(f"  INDIA {i}/{len(INDIA_URLS)}: {url}")
        data = scrape_india(url)
        _save_scraped_data("INDIA", data, save_india)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="INDIA", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # 🅴 SCHOLARSHIP
    print(f"Processing SCHOLARSHIP ({len(SCHOLARSHIP_URLS)} URLs)...")
    for i, url in enumerate(SCHOLARSHIP_URLS, 1):
        print(f"  SCHOLARSHIP {i}/{len(SCHOLARSHIP_URLS)}: {url}")
        data = scrape_scholarship(url)
        _save_scraped_data("SCHOLARSHIP", data, save_scholarship)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="SCHOLARSHIP", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # 🅵 GRANTS
    print(f"Processing GRANTS ({len(GRANT_URLS)} URLs)...")
    for i, url in enumerate(GRANT_URLS, 1):
        print(f"  GRANTS {i}/{len(GRANT_URLS)}: {url}")
        data = scrape_grants(url)
        _save_scraped_data("GRANTS", data, save_grants)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source="GRANTS", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    # TENDERS
    print(f"Processing TENDERS ({len(TENDER_URLS)} sources)...")
    for i, (source_name, url) in enumerate(TENDER_URLS.items(), 1):
        print(f"  TENDERS {i}/{len(TENDER_URLS)} ({source_name}): {url}")
        data = scrape_tenders(source_name, url)
        _save_scraped_data("TENDERS", data, save_tender_listings)
        processed += 1
        if progress_callback:
            progress_callback(processed=processed, total=total_urls, source=f"TENDERS: {source_name}", url=url)
        print(f"    Saved {len(data)} items. Total processed: {processed}/{total_urls}")

    print(f"Scraping completed! Total URLs processed: {processed}")
    print("Scrape successfully. Data stored to MongoDB successfully.")

"""
Week 5 - Assignment A9: The Polite Scraper
Pipeline: Fetch -> Extract -> Normalize -> Validate -> Store -> Report
"""
import hashlib
from datetime import datetime, timezone
import json
import os
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from schema import BookRecord

# Configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks)"
TIMEOUT_SECONDS = 5
POLITE_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3

OUTPUT_DIR = "output"
BOOKS_FILE = os.path.join(OUTPUT_DIR, "books.json")
ERRORS_FILE = os.path.join(OUTPUT_DIR, "errors.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "run-report.json")

stats = {
    "pages_fetched" : 0,
    "cache_hits" : 0,
    "failed_pages" : 0,
}


def get_cache_path_for_url(url: str, prefix: str = "page") -> str:
    """Generates a stable cache filename based on a SHA-256 hash of the URL."""
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return os.path.join("cache", f"{prefix}-{url_hash}.html")


def fetch_page(url: str, cache_file: str) -> str:
    """
    Politely fetches a page with local caching, timeout, UTF-8 decoding,
    and a 1-time retry for transient network/5xx errors (never retrying 404/403).
    """
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()
        stats["cache_hits"] += 1
        print(f"CACHE HIT: {cache_file} ({len(html.encode('utf-8'))} bytes)")
        return html

    headers = {"User-Agent": USER_AGENT}
    attempts = 0
    max_attempts = 2

    while attempts < max_attempts:
        attempts += 1
        time.sleep(POLITE_DELAY_SECONDS)

        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

            # Do not retry client rejections / not-found
            if response.status_code in (403, 404):
                raise RuntimeError(
                    f"HTTP {response.status_code} on {url} - will not retry"
                )

            # Check for server-side errors
            if 500 <= response.status_code < 600:
                if attempts < max_attempts:
                    print(f"Server error {response.status_code} on {url}. Retrying once...")
                    time.sleep(1.0)
                    continue
                raise RuntimeError(f"Server error {response.status_code} on {url}")

            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to fetch {url}: status code {response.status_code}"
                )

            response.encoding = "utf-8"
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(response.text)

            stats["pages_fetched"] += 1
            print(f"FETCH: {url} ({len(response.content)} bytes)")
            return response.text

        except (requests.Timeout, requests.ConnectionError) as net_err:
            if attempts < max_attempts:
                print(f"Transient error ({net_err.__class__.__name__}) on {url}. Retrying once...")
                time.sleep(1.0)
                continue
            raise RuntimeError(f"Network failure on {url}: {str(net_err)}")



def discover_books():
    """
    Traverses the first 3 catalogue pages dynamically, extracting all unique book links.
    """
    current_url = START_URL
    discovered_items = []
    catalogue_pages_visited = 0

    while current_url and catalogue_pages_visited < MAX_CATALOGUE_PAGES:
        catalogue_pages_visited += 1
        cache_path = os.path.join("cache", f"catalogue-page-{catalogue_pages_visited}.html")
        
        html = fetch_page(current_url, cache_path)
        soup = BeautifulSoup(html, "html.parser")

        # Extract book links
        book_tags = soup.select("article.product_pod h3 a")
        for tag in book_tags:
            relative_href = tag.get("href")
            if relative_href:
                absolute_url = urljoin(current_url, relative_href)
                discovered_items.append({
                    "product_url": absolute_url,
                    "source_page": current_url
                })

        # Discover next catalogue page
        next_tag = soup.select_one("li.next a")
        if next_tag and next_tag.get("href"):
            next_href = next_tag.get("href")
            current_url = urljoin(current_url, next_href)
        else:
            current_url = None

    seen_urls = set()
    unique_items = []
    for item in discovered_items:
        if item["product_url"] not in seen_urls:
            seen_urls.add(item["product_url"])
            unique_items.append(item)

    return unique_items


def extract_book_detail(product_url: str, source_page: str) -> dict:
    """Extracts raw record fields from a single book detail page."""
    cache_path = get_cache_path_for_url(product_url, prefix="book")
    html = fetch_page(product_url, cache_path)
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_elem = soup.select_one(".product_main h1")
    title = title_elem.get_text(strip=True) if title_elem else ""

    # Price
    price_elem = soup.select_one(".product_main .price_color")
    price_text = ""
    if price_elem:
        # Normalize and remove stray encoding artifacts directly
        price_text = price_elem.get_text(strip=True).replace("\u00a0", " ")
        if price_text.startswith("Â£"):
            price_text = price_text.replace("Â£", "£")

    # Availability
    avail_elem = soup.select_one(".product_main .availability")
    availability_text = avail_elem.get_text(strip=True) if avail_elem else ""

    # Star Rating
    rating_elem = soup.select_one(".product_main .star-rating")
    rating_text = ""
    if rating_elem:
        classes = rating_elem.get("class", [])
        rating_classes = [c for c in classes if c != "star-rating"]
        rating_text = rating_classes[0] if rating_classes else ""

    # Description (#product_description + p)
    desc_header = soup.select_one("#product_description")
    description = None
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True)

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }


def normalize_price(price_text: str) -> float:
    """Extracts numeric float from text."""
    clean_number = re.sub(r"[^\d.]", "", price_text)
    return float(clean_number) if clean_number else 0.0


def main():
    start_time_iso = datetime.now(timezone.utc).isoformat()
    t0 = time.time()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    books_to_scrape = discover_books()

    # --- STAGE 5 RESILIENCE PROOF INJECTION ---
    # Intentionally inject one bogus URL to prove failure survival
    books_to_scrape.append({
        "product_url": "https://books.toscrape.com/catalogue/non-existent-book_9999/index.html",
        "source_page": "https://books.toscrape.com/catalogue/page-1.html"
    })

    valid_records = []
    error_records = []

    # Handle each item in complete isolation
    for item in books_to_scrape:
        url = item["product_url"]
        src = item["source_page"]

        try:
            raw_data = extract_book_detail(url, src)
        except Exception as page_err:
            stats["failed_pages"] += 1
            print(f"SKIPPED BROKEN PAGE: {url} -> {str(page_err)}")
            error_records.append({
                "product_url": url,
                "reason": f"Fetch/Extraction failure: {str(page_err)}"
            })
            continue

        normalized_data = dict(raw_data)
        try:
            normalized_data["price_gbp"] = normalize_price(raw_data["price_text"])
        except Exception as norm_err:
            error_records.append({"raw_data": raw_data, "reason": f"Normalization error: {str(norm_err)}"})
            continue

        try:
            validated = BookRecord(**normalized_data)
            valid_records.append(validated.model_dump(mode="json"))
        except ValidationError as err:
            error_records.append({"raw_data": normalized_data, "reason": err.errors()})


    # Idempotent writes
    with open(BOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)

    with open(ERRORS_FILE, "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2, ensure_ascii=False)

    # End run and write telemetry report
    duration_ms = int((time.time() - t0) * 1000)
    report_data = {
        "start_time": start_time_iso,
        "duration_ms": duration_ms,
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(error_records) - stats["failed_pages"],
        "failed_pages": stats["failed_pages"]
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n--- RUN FINISHED ---")
    print(f"Valid records : {len(valid_records)}")
    print(f"Failed pages  : {stats['failed_pages']}")
    print(f"Report saved  : {REPORT_FILE}")


if __name__ == "__main__":
    main()

    
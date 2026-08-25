"""
Week 5 - Assignment A9: The Polite Scraper
Pipeline: Fetch -> Extract -> Normalize -> Validate -> Store -> Report
"""
import hashlib
from datetime import datetime, timezone
import json
import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# Configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks)"
TIMEOUT_SECONDS = 5
POLITE_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3


def get_cache_path_for_url(url: str, prefix: str = "page") -> str:
    """Generates a stable cache filename based on a SHA-256 hash of the URL."""
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return os.path.join("cache", f"{prefix}-{url_hash}.html")


def fetch_page(url: str, cache_file: str) -> str:
    """
    Politely fetches a page with local caching, custom user-agent, timeout,
    and a rate-limiting delay on live requests.
    """
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_file} ({len(html.encode('utf-8'))} bytes)")
        return html

    # Rate limiting on real network calls
    time.sleep(POLITE_DELAY_SECONDS)

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: received status code {response.status_code}"
        )

    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"FETCH: {url} ({len(response.content)} bytes)")
    return response.text


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
    price_text = price_elem.get_text(strip=True) if price_elem else ""

    # Availability
    avail_elem = soup.select_one(".product_main .availability")
    availability_text = avail_elem.get_text(strip=True) if avail_elem else ""

    # Star Rating (e.g., class "star-rating Three")
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


def main():
    books_to_scrape = discover_books()
    raw_records = []

    for item in books_to_scrape:
        record = extract_book_detail(item["product_url"], item["source_page"])
        raw_records.append(record)

    if raw_records:
        print("\n--- SAMPLE RAW RECORD ---")
        print(json.dumps(raw_records[0], indent=2))

    print(f"\ndetail_pages={len(raw_records)}")


if __name__ == "__main__":
    main()
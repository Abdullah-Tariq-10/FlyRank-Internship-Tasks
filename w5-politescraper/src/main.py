"""
Week 5 - Assignment A9: The Polite Scraper
Pipeline: Fetch -> Extract -> Normalize -> Validate -> Store -> Report
"""
import os
import time
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks)"
TIMEOUT_SECONDS = 5
POLITE_DELAY_SECONDS = 0.5
MAX_CATALOGUE_PAGES = 3

def get_cache_path_for_catalogue(page_number: int) -> str:
    """Returns the local cache path for a catalogue page."""
    return os.path.join("cache", f"catalogue-page-{page_number}.html")

def fetch_page(url : str, cache_file: str) -> str:
    """
    Politely fetches a page with local caching, custom user-agent, timeout,
    and a rate-limiting delay on live requests.
    """
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_file} ({len(html.encode('utf-8'))} bytes)")
        return html

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

    print(f"FETCH : {url} ({len(response.content)} bytes)")
    return response.text

def discover_books():
    """
    Traverses the first 3 catalogue pages dynamically, extracting all unique book links.
    """
    current_url = START_URL
    discovered_urls = []
    catalogue_pages_visited = 0

    while current_url and catalogue_pages_visited < MAX_CATALOGUE_PAGES:
        catalogue_pages_visited += 1
        cache_path = get_cache_path_for_catalogue(catalogue_pages_visited)
        
        html = fetch_page(current_url, cache_path)
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract all book detail page links on the current catalogue page
        # Each book pod has an h3 containing an anchor <a>
        book_tags = soup.select("article.product_pod h3 a")
        for tag in book_tags:
            relative_href = tag.get("href")
            if relative_href:
                # Resolve relative URL against current page URL
                absolute_url = urljoin(current_url, relative_href)
                discovered_urls.append(absolute_url)

        # 2. Discover next catalogue page via pagination link (li.next > a)
        next_tag = soup.select_one("li.next a")
        if next_tag and next_tag.get("href"):
            next_href = next_tag.get("href")
            current_url = urljoin(current_url, next_href)
        else:
            current_url = None

    # Remove duplicates while preserving order
    unique_urls = list(dict.fromkeys(discovered_urls))

    print(
        f"catalogue_pages={catalogue_pages_visited}, "
        f"discovered={len(discovered_urls)}, "
        f"unique_urls={len(unique_urls)}"
    )

    return unique_urls


def main():
    discover_books()


if __name__ == "__main__":
    main()
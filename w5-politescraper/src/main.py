"""
Week 5 - Assignment A9: The Polite Scraper
Pipeline: Fetch -> Extract -> Normalize -> Validate -> Store -> Report
"""
import os
import requests

TARGET_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_PATH = os.path.join("cache", "catalogue-page-1.html")
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks)"
TIMEOUT_SECONDS = 5


def fetch_page(url: str, cache_file: str) -> str:
    """
    Fetch a page politely with caching, timeout, and status verification.
    """

    # 1. Checking local cache first
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()
        print(f"CACHE HIT: {cache_file} ({len(html.encode('utf-8'))} bytes)")
        return html

    # 2. Make polite request if not cached
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)

    # 3. Verify status code
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: received status code {response.status_code}"
        )

    # 4. Save to cache
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"FETCH: {url} ({len(response.content)} bytes)")
    return response.text


def main():
    fetch_page(TARGET_URL, CACHE_PATH)

if __name__ == "__main__":
    main()
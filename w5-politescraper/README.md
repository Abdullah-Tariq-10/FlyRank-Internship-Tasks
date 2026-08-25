# The Polite Scraper (A9)

A polite, resilient web scraping pipeline built with Python, Requests, BeautifulSoup, and Pydantic.

## Target Classification

- **Target Site:** `https://books.toscrape.com/`
- **Purpose:** Educational sandbox created explicitly for testing and practising web scraping.
- **Scope:** First 3 catalogue pages only (60 total book items).
- **Data Collected:** `title`, `product_url`, `price_text`, `price_gbp`, `availability_text`, `rating_text`, `description`, `source_page`, `fetched_at`.
- **Why Appropriate:** The site is a non-production public sandbox designed for automated scrapers, generating no load on commercial business infrastructure.
- **Robots.txt Check:** `https://books.toscrape.com/robots.txt` returned `404 Not Found` (no robots file found).

> "I will not reuse this code on another site without checking its rules and terms first."
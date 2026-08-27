# The Polite Scraper W4(A9)

A resilient, production-grade web scraping pipeline built in Python using **Requests**, **BeautifulSoup4**, and **Pydantic**[cite: 3]. It traverses the catalogue of an educational sandbox, extracts raw fields across 60 book detail pages, normalizes numeric values, enforces schema contracts, isolates page failures, performs stateful Change Data Capture (CDC), and outputs run telemetry[cite: 3].

---

## 🎯 Target Classification & Ethics

- **Target Site:** `https://books.toscrape.com/`[cite: 3]
- **Purpose:** Educational sandbox explicitly built for practising web scraping[cite: 3].
- **Scope:** First 3 catalogue pages only (60 unique books)[cite: 3].
- **Data Collected:** Product title, canonical URL, raw price, normalized price (GBP), stock status, star rating, description, discovery source, and fetch timestamp[cite: 3].
- **Robots.txt Result:** Missing (`404 Not Found` — treated as no robots file found)[cite: 3].
- **No Headless Browser Required:** All content is statically rendered in server-side HTML[cite: 3]. Fetching raw HTML directly via HTTP avoids the CPU, memory, and latency overhead of spinning up a headless browser (such as Chromium/Playwright)[cite: 3].
- **Ethics Statement:** *"I will not reuse this code on another site without checking its rules and terms first."*[cite: 3] Always prioritize official APIs when available, never bypass authentication or paywalls, and extract only the data necessary for the task[cite: 3].

---

## 🏗️ Pipeline Architecture

```text
[ Books to Scrape (HTML) ]
             │
      1. Fetch (Requests + Timeout + Custom User-Agent + Exponential Retry)
             │
      2. Cache (Local .html files to avoid repeat server hits)
             │
      3. Extract (BeautifulSoup DOM selectors -> 8 raw string fields)
             │
      4. Normalize (Regex string parsing -> price_gbp numeric float)
             │
      5. Validate (Pydantic BookRecord schema -> type & URL constraints)
             │
     ┌───────┴───────┐
  [Valid]        [Invalid]
     │               │
  output/         output/
 books.json      errors.json
     │               │
     └───────┬───────┘
             │
      6. Change Detection (CDC state diffing vs output/state.json)
             │
      7. Telemetry Report (output/run-report.json)

```

---

## 📋 Data Schema

Every validated record in `output/books.json` strictly adheres to the following contract defined in `src/schema.py`:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `str` | Yes | Full product title

 |
| `product_url` | `HttpUrl` | Yes | Canonical, absolute HTTPS URL

 |
| `price_text` | `str` | Yes | Raw scraped price string (e.g., `"£51.77"`)

 |
| `price_gbp` | `float` | Yes | Cleaned numeric price (`>= 0.0`)

 |
| `availability_text` | `str` | Yes | In-stock status text

 |
| `rating_text` | `str` | Yes | Rating word (`"One"`, `"Two"`, `"Three"`, etc.)

 |
| `description` | `Optional[str]` | No | Product description text (`null` if absent)

 |
| `source_page` | `HttpUrl` | Yes | Absolute catalogue URL where link was discovered

 |
| `fetched_at` | `str` | Yes | ISO-8601 UTC timestamp of extraction

 |

---

## 🤝 Politeness & Reliability Controls

* **Honest User-Agent:** Introduces the scraper with repository provenance: `FlyRankInternship-A9/1.0 (+https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks)`.


* **Local Disk Caching:** Raw HTML responses are saved to `cache/` hashed by URL. Development iterations read directly from disk, preventing unnecessary traffic to the host server.


* **Strict Timeouts:** Enforces a 5-second upper limit per HTTP call.


* **Polite Delays:** Sleeps $\ge 500\text{ ms}$ between live network requests (cached reads execute with 0 delay).


* **Intelligent Retry Rules:** Automatically retries transient `5xx` server errors and network timeouts once after a pause, while immediately failing fast on `404 Not Found` and `403 Forbidden`.


* **Fault Isolation:** Per-page `try/except` boundaries ensure that a broken or missing detail page is logged to `output/errors.json` and does not terminate the remaining queue.


* **Idempotency:** Re-running the pipeline overwrites output datasets cleanly, producing the exact same 60 records rather than duplicating them.



---

## 🌟 Implemented Extras

### 1. Offline Parser Fixtures & Unit Tests (`pytest`)

Automated test suite (`tests/test_parser.py`) testing parser edge cases against offline HTML fixtures (`tests/fixtures/`) without making live network requests:

* Price normalization and currency symbol removal (`£`, `Â£`, extra whitespace).


* RFC-compliant relative-to-absolute URL resolution.


* Handling missing `<div id="product_description">` elements by defaulting to `None`.


* Handling unicode artifacts and non-breaking spaces.


* Pydantic schema validation rejecting invalid payloads.



### 2. Hash-Based Change Detection (CDC)

Tracks state mutations across runs by storing SHA-256 content fingerprints in `output/state.json`. Telemetry classifies records into `new`, `changed`, `unchanged`, and `deleted`.

---

## 📊 Run Telemetry

Sample execution report from `output/run-report.json`:

```json
{
  "start_time": "2026-08-26T16:09:06.225762+00:00",
  "duration_ms": 5167,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1,
  "change_detection": {
    "new": 0,
    "changed": 0,
    "unchanged": 60,
    "deleted": 0
  }
}

```

---

## 🚀 Setup & Execution

### 1. Clone & Navigate

```bash
git clone [https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks.git](https://github.com/Abdullah-Tariq-10/FlyRank-Internship-Tasks.git)
cd FlyRank-Internship-Tasks/w5-politescraper

```

### 2. Environment Setup

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

```

### 3. Run the Scraper

```bash
python src/main.py

```

### 4. Run Unit Tests

```bash
pytest -v

```

```

```
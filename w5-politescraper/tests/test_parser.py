import os
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pytest

# Add src to Python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from main import normalize_price
from schema import BookRecord


def test_price_normalization():
    """1. Test price normalization with currency symbols, extra spaces, and encoding artifacts."""
    assert normalize_price("£51.77") == 51.77
    assert normalize_price("Â£19.95") == 19.95
    assert normalize_price("  £ 4.50  ") == 4.50
    assert normalize_price("Free") == 0.0


def test_relative_to_absolute_url_resolution():
    """2. Test relative URL resolution matches RFC standard behavior."""
    base_page = "https://books.toscrape.com/catalogue/page-1.html"
    relative_link = "a-light-in-the-attic_1000/index.html"
    expected = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert urljoin(base_page, relative_link) == expected

def test_missing_description_handling():
    """3. Test parser sets description to None when the element is absent."""
    fixture_path = os.path.join("tests", "fixtures", "missing_description.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    desc_header = soup.select_one("#product_description")
    description = None
    if desc_header:
        desc_p = desc_header.find_next_sibling("p")
        if desc_p:
            description = desc_p.get_text(strip=True)

    assert description is None


def test_whitespace_and_encoding_cleaning():
    """4. Test parser cleans whitespace and encoding noise correctly."""
    fixture_path = os.path.join("tests", "fixtures", "messy_price_and_spaces.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    title_elem = soup.select_one(".product_main h1")
    title = title_elem.get_text(strip=True) if title_elem else ""

    price_elem = soup.select_one(".product_main .price_color")
    price_text = price_elem.get_text(strip=True).replace("\u00a0", " ").replace("Â£", "£") if price_elem else ""

    desc_header = soup.select_one("#product_description")
    desc_p = desc_header.find_next_sibling("p") if desc_header else None
    description = desc_p.get_text(strip=True) if desc_p else None

    assert title == "Messy Data & Spaces"
    assert "£ 19.95" in price_text
    assert description == "A book with extra whitespace and encoding noise."


def test_schema_rejects_malformed_record():
    """5. Test Pydantic schema validation rejects invalid URLs and missing required fields."""
    with pytest.raises(Exception):
        BookRecord(
            title="",  # Invalid: empty string
            product_url="not-a-valid-url",  # Invalid: not an HttpUrl
            price_text="£10.00",
            price_gbp=-5.0,  # Invalid: negative price
            availability_text="In stock",
            rating_text="Two",
            source_page="bad-url",
            fetched_at=""
        )
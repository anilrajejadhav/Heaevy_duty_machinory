"""Load catalogue files into small, searchable records."""

from __future__ import annotations

import csv
import hashlib
import logging
import re
from pathlib import Path

from pypdf import PdfReader

from app.models import CatalogItem


LOGGER = logging.getLogger(__name__)
REFERENCE_PATTERN = re.compile(r"\bREF\s*\d{3}TA\d{4}\b", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Normalize whitespace without changing product codes or punctuation."""
    return re.sub(r"\s+", " ", text).strip()


def find_references(text: str) -> list[str]:
    """Extract and normalize article references found in a text block."""
    matches = {re.sub(r"\s+", " ", match.upper()) for match in REFERENCE_PATTERN.findall(text)}
    return sorted(matches)


def make_item(source: Path, text: str, page: int | None = None) -> CatalogItem | None:
    """Create one record only when the source contains meaningful text."""
    cleaned_text = clean_text(text)
    if len(cleaned_text) < 20:
        return None
    unique_value = f"{source.resolve()}:{page}:{cleaned_text[:100]}"
    item_id = hashlib.sha1(unique_value.encode("utf-8")).hexdigest()[:16]
    return CatalogItem(
        item_id=item_id,
        source=source.name,
        page=page,
        text=cleaned_text,
        reference_numbers=find_references(cleaned_text),
    )


def load_pdf(path: Path, max_pages: int = 0) -> list[CatalogItem]:
    """Extract one searchable record per PDF page.

    Keeping pages intact preserves the page number that a user needs to find
    the article again in the original catalogue.
    """
    reader = PdfReader(str(path))
    page_count = len(reader.pages) if max_pages == 0 else min(len(reader.pages), max_pages)
    items: list[CatalogItem] = []
    for page_index in range(page_count):
        item = make_item(path, reader.pages[page_index].extract_text() or "", page_index + 1)
        if item:
            items.append(item)
    LOGGER.info("Loaded %s searchable pages from %s", len(items), path.name)
    return items


def load_text(path: Path) -> list[CatalogItem]:
    """Load a plain-text catalogue as one record per non-empty line."""
    items: list[CatalogItem] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        item = make_item(path, line, line_number)
        if item:
            items.append(item)
    return items


def load_csv(path: Path) -> list[CatalogItem]:
    """Turn each non-empty CSV row into a searchable product record."""
    items: list[CatalogItem] = []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as file:
        for row_number, row in enumerate(csv.DictReader(file), 2):
            row_text = " ".join(f"{key}: {value}" for key, value in row.items() if value)
            item = make_item(path, row_text, row_number)
            if item:
                items.append(item)
    return items


def load_file(path: Path, max_pages_per_pdf: int = 0) -> list[CatalogItem]:
    """Load one supported catalogue source."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, max_pages_per_pdf)
    if suffix == ".txt":
        return load_text(path)
    if suffix == ".csv":
        return load_csv(path)
    raise ValueError(f"Unsupported source type: {suffix}")

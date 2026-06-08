"""
Extract plain text from PDF files for text-only translation mode.

Layout, images, and tables are not preserved. Paragraphs are inferred from
line breaks and vertical gaps between text blocks on each page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_PARAGRAPH_BREAK = re.compile(r"\n{2,}")
_SHORT_LINE = re.compile(r"^.{1,80}$")
_ALL_CAPS = re.compile(r"^[A-Z0-9][A-Z0-9\s\-:,.']{2,}$")


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be read or yields no extractable text."""


@dataclass
class ExtractedPdf:
    """Normalized text extracted from a PDF."""

    paragraphs: List[str] = field(default_factory=list)
    page_count: int = 0
    source_path: str = ""

    @property
    def plain_text(self) -> str:
        return "\n\n".join(self.paragraphs)


def _normalize_page_text(raw: str) -> List[str]:
    """Turn raw page text into paragraph blocks."""
    if not raw or not raw.strip():
        return []

    lines = [line.strip() for line in raw.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return []

    blocks: List[str] = []
    current: List[str] = []

    def flush() -> None:
        if current:
            blocks.append(" ".join(current))
            current.clear()

    for line in lines:
        if not current:
            current.append(line)
            continue
        prev = current[-1]
        # New paragraph when the previous line ends a sentence or the new line
        # looks like a heading / list item.
        if prev.endswith((".", "!", "?", ":", ";")) or _SHORT_LINE.match(line) and _ALL_CAPS.match(line):
            flush()
        current.append(line)
    flush()
    return blocks


def _merge_page_paragraphs(pages: List[List[str]]) -> List[str]:
    """Flatten per-page paragraphs, inserting page-break markers sparingly."""
    merged: List[str] = []
    for page_index, page_paragraphs in enumerate(pages):
        if not page_paragraphs:
            continue
        if merged and page_index > 0:
            # Keep a lightweight page boundary hint for markdown writers.
            merged.append("")
        merged.extend(page_paragraphs)
    # Collapse accidental empty runs while preserving intentional blanks.
    cleaned: List[str] = []
    for para in merged:
        text = (para or "").strip()
        if not text:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        cleaned.append(text)
    return [p for p in cleaned if p != ""] or cleaned


def extract_pdf_text(file_path: str) -> ExtractedPdf:
    """
    Extract readable text from a PDF file.

    Args:
        file_path: Path to the input PDF.

    Returns:
        ExtractedPdf with paragraph list and metadata.

    Raises:
        PdfExtractionError: On I/O failures, invalid PDFs, or empty extraction.
    """
    path = Path(file_path)
    if not path.is_file():
        raise PdfExtractionError(f"PDF file not found: {file_path}")

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfExtractionError(
            "PDF support requires the 'pypdf' package. Install project dependencies."
        ) from exc

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise PdfExtractionError(f"Cannot open PDF '{path.name}': {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise PdfExtractionError(
                f"PDF '{path.name}' is encrypted and cannot be decrypted."
            ) from exc

    page_paragraphs: List[List[str]] = []
    for page in reader.pages:
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        page_paragraphs.append(_normalize_page_text(raw))

    paragraphs = _merge_page_paragraphs(page_paragraphs)
    if not paragraphs or not any(p.strip() for p in paragraphs):
        raise PdfExtractionError(
            f"No extractable text found in PDF '{path.name}'. "
            "Scanned/image-only PDFs are not supported in text-only mode."
        )

    return ExtractedPdf(
        paragraphs=paragraphs,
        page_count=len(reader.pages),
        source_path=str(path),
    )


def paragraphs_to_chunk_text(paragraphs: List[str]) -> str:
    """Join paragraphs for token-based chunking (same separator as plain-text mode)."""
    return "\n\n".join(p.strip() for p in paragraphs if (p or "").strip())

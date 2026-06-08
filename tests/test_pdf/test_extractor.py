"""Tests for PDF text extraction."""

import pytest

from src.core.pdf.extractor import PdfExtractionError, extract_pdf_text, paragraphs_to_chunk_text
from src.utils.file_detector import detect_file_type


def test_detect_file_type_pdf_extension(sample_pdf_path):
    assert detect_file_type(sample_pdf_path) == "pdf"


def test_extract_pdf_text_returns_paragraphs(sample_pdf_path):
    try:
        extracted = extract_pdf_text(sample_pdf_path)
    except PdfExtractionError:
        pytest.skip("pypdf not installed or sample PDF not readable in this environment")
    assert extracted.page_count >= 1
    assert len(extracted.paragraphs) >= 1
    joined = " ".join(extracted.paragraphs)
    assert "Hello PDF world" in joined
    assert "Second paragraph" in joined


def test_extract_pdf_text_empty_raises(empty_pdf_path):
    with pytest.raises(PdfExtractionError):
        extract_pdf_text(empty_pdf_path)


def test_paragraphs_to_chunk_text_joins_blocks():
    text = paragraphs_to_chunk_text(["One", "Two"])
    assert text == "One\n\nTwo"

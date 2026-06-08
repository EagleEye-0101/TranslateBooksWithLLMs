"""Tests for PdfAdapter."""

from unittest.mock import patch

import pytest

from src.core.adapters.pdf_adapter import PdfAdapter
from src.core.pdf.extractor import ExtractedPdf


@pytest.fixture
def extracted_sample():
    return ExtractedPdf(
        paragraphs=[
            "CHAPTER ONE",
            "Hello PDF world. This is paragraph one.",
            "Second paragraph for testing.",
        ],
        page_count=1,
        source_path="sample.pdf",
    )


@pytest.mark.asyncio
async def test_pdf_adapter_prepare_and_units(sample_pdf_path, tmp_path, extracted_sample):
    output_path = tmp_path / "out.md"
    adapter = PdfAdapter(
        input_file_path=sample_pdf_path,
        output_file_path=str(output_path),
        config={"max_tokens_per_chunk": 500},
    )

    with patch("src.core.adapters.pdf_adapter.extract_pdf_text", return_value=extracted_sample):
        assert await adapter.prepare_for_translation() is True

    units = adapter.get_translation_units()
    assert len(units) >= 1
    assert adapter.format_name == "pdf"


@pytest.mark.asyncio
async def test_pdf_adapter_reconstruct_markdown(sample_pdf_path, tmp_path, extracted_sample):
    output_path = tmp_path / "out.md"
    adapter = PdfAdapter(
        input_file_path=sample_pdf_path,
        output_file_path=str(output_path),
        config={"pdf_output_extension": ".md"},
    )

    with patch("src.core.adapters.pdf_adapter.extract_pdf_text", return_value=extracted_sample):
        await adapter.prepare_for_translation()

    for index, unit in enumerate(adapter.get_translation_units()):
        await adapter.save_unit_translation(unit.unit_id, f"[FR] {unit.content}")

    data = await adapter.reconstruct_output()
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "[FR]" in text
    assert len(data) > 0


@pytest.mark.asyncio
async def test_pdf_adapter_reconstruct_docx(sample_pdf_path, tmp_path, extracted_sample):
    output_path = tmp_path / "out.docx"
    adapter = PdfAdapter(
        input_file_path=sample_pdf_path,
        output_file_path=str(output_path),
        config={"pdf_output_extension": ".docx"},
    )

    with patch("src.core.adapters.pdf_adapter.extract_pdf_text", return_value=extracted_sample):
        await adapter.prepare_for_translation()

    unit = adapter.get_translation_units()[0]
    await adapter.save_unit_translation(unit.unit_id, "Translated paragraph")

    await adapter.reconstruct_output()
    assert output_path.exists()
    assert output_path.stat().st_size > 0

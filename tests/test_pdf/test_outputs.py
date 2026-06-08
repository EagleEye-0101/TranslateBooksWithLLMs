"""Tests for PDF output writers."""

from pathlib import Path

from docx import Document

from src.core.pdf.output_writers import (
    resolve_output_extension,
    write_docx,
    write_markdown,
    write_translated_output,
    write_txt,
)


def test_resolve_output_extension_defaults_to_txt():
    assert resolve_output_extension("book.pdf") == ".txt"
    assert resolve_output_extension("book.out.md") == ".md"


def test_write_txt_md_docx(tmp_path):
    paragraphs = ["CHAPTER ONE", "Body paragraph one.", "Body paragraph two."]
    txt_path = tmp_path / "out.txt"
    md_path = tmp_path / "out.md"
    docx_path = tmp_path / "out.docx"

    write_txt(paragraphs, txt_path)
    write_markdown(paragraphs, md_path)
    write_docx(paragraphs, docx_path)

    assert "CHAPTER ONE" in txt_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")
    assert "## CHAPTER ONE" in md_text
    assert "Body paragraph one." in md_text

    document = Document(str(docx_path))
    doc_paras = [p.text for p in document.paragraphs if p.text.strip()]
    assert any("CHAPTER ONE" in p for p in doc_paras)
    assert any("Body paragraph one." in p for p in doc_paras)


def test_write_translated_output_honors_extension(tmp_path):
    paragraphs = ["Only paragraph"]
    out = tmp_path / "result"
    ext = write_translated_output(paragraphs, out.with_suffix(".docx"))
    assert ext == ".docx"
    assert out.with_suffix(".docx").exists()

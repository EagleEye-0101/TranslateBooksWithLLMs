"""Shared fixtures for PDF tests."""

import os
from pathlib import Path

import pytest


def _build_text_pdf_bytes(lines: list[str]) -> bytes:
    """Build a minimal valid PDF with extractable Type1 text."""
    text_ops = ["BT /F1 12 Tf 72 720 Td"]
    for index, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index == 0:
            text_ops.append(f"({safe}) Tj")
        else:
            text_ops.append("T*")
            text_ops.append(f"({safe}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")
    stream_header = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
    stream_footer = b"\nendstream"

    parts = [
        b"%PDF-1.4\n",
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        (
            b"3 0 obj<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
            b"/MediaBox [0 0 612 792] /Contents 5 0 R >>endobj\n"
        ),
        b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
        b"5 0 obj",
        stream_header,
        stream,
        stream_footer,
        b"\nendobj\n",
        b"xref\n0 6\n0000000000 65535 f \n",
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n0\n%%EOF\n",
    ]
    return b"".join(parts)


@pytest.fixture
def sample_pdf_path(tmp_path):
    path = tmp_path / "sample.pdf"
    path.write_bytes(
        _build_text_pdf_bytes(
            [
                "CHAPTER ONE",
                "Hello PDF world. This is paragraph one.",
                "Second paragraph for testing extraction.",
            ]
        )
    )
    yield str(path)


@pytest.fixture
def empty_pdf_path(tmp_path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(
        _build_text_pdf_bytes([""])
    )
    yield str(path)

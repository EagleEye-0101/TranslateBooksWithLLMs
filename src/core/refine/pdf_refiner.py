"""
PDF refine-only mode (text-only).

Extracts text from a PDF assumed to already be in the target language,
runs the same refinement chunk pipeline as TXT, then writes .txt/.md/.docx.
"""

import os
from typing import Optional, Callable, Dict, Any

from src.core.pdf.extractor import PdfExtractionError, extract_pdf_text, paragraphs_to_chunk_text
from src.core.pdf.output_writers import resolve_output_extension, write_translated_output
from src.core.text_processor import split_text_into_chunks
from src.core.translator import refine_chunks
from src.config import DEFAULT_MODEL, API_ENDPOINT


async def refine_pdf_file(
    input_filepath: str,
    output_filepath: str,
    target_language: str,
    model_name: str = DEFAULT_MODEL,
    cli_api_endpoint: str = API_ENDPOINT,
    log_callback: Optional[Callable] = None,
    stats_callback: Optional[Callable] = None,
    check_interruption_callback: Optional[Callable] = None,
    llm_provider: str = "ollama",
    gemini_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    poe_api_key: Optional[str] = None,
    nim_api_key: Optional[str] = None,
    context_window: int = 2048,
    auto_adjust_context: bool = True,
    max_tokens_per_chunk: Optional[int] = None,
    soft_limit_ratio: Optional[float] = None,
    prompt_options: Optional[Dict[str, Any]] = None,
    pdf_output_extension: Optional[str] = None,
) -> bool:
    """Refine text extracted from a PDF and write structured output."""
    if not os.path.exists(input_filepath):
        err_msg = f"ERROR: Input file '{input_filepath}' not found."
        if log_callback:
            log_callback("file_not_found_error", err_msg)
        return False

    try:
        extracted = extract_pdf_text(input_filepath)
    except PdfExtractionError as exc:
        if log_callback:
            log_callback("pdf_extract_error", f"ERROR: {exc}")
        return False

    translated_text = paragraphs_to_chunk_text(extracted.paragraphs)
    chunks = split_text_into_chunks(
        text=translated_text,
        max_tokens_per_chunk=max_tokens_per_chunk,
        soft_limit_ratio=soft_limit_ratio,
    )

    draft_chunks = [c["main_content"] for c in chunks]
    refined_parts = await refine_chunks(
        translated_chunks=draft_chunks,
        original_chunks=chunks,
        target_language=target_language,
        model_name=model_name,
        api_endpoint=cli_api_endpoint,
        log_callback=log_callback,
        stats_callback=stats_callback,
        check_interruption_callback=check_interruption_callback,
        llm_provider=llm_provider,
        gemini_api_key=gemini_api_key,
        openai_api_key=openai_api_key,
        openrouter_api_key=openrouter_api_key,
        mistral_api_key=mistral_api_key,
        deepseek_api_key=deepseek_api_key,
        poe_api_key=poe_api_key,
        nim_api_key=nim_api_key,
        context_window=context_window,
        auto_adjust_context=auto_adjust_context,
        prompt_options=prompt_options or {},
    )

    refined_text = "\n".join(refined_parts)
    paragraphs = [p.strip() for p in refined_text.split("\n\n") if p.strip()]
    ext = pdf_output_extension or resolve_output_extension(output_filepath)
    write_translated_output(paragraphs, output_filepath, output_extension=ext)

    if log_callback:
        log_callback("refine_complete", f"Refined PDF text saved: {output_filepath}")
    return True

"""
PDF format adapter for text-only translation.

Extracts text from a PDF, translates it through the generic chunk pipeline,
then writes the result as .txt, .md, or .docx depending on the output path.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .format_adapter import FormatAdapter
from .translation_unit import TranslationUnit
from src.core.pdf.extractor import (
    PdfExtractionError,
    extract_pdf_text,
    paragraphs_to_chunk_text,
)
from src.core.pdf.output_writers import write_translated_output


class PdfAdapter(FormatAdapter):
    """Adapter for PDF files in text-only mode."""

    def __init__(self, input_file_path: str, output_file_path: str, config: Dict[str, Any]):
        super().__init__(input_file_path, output_file_path, config)
        self.paragraphs: List[str] = []
        self.chunks: List[Dict[str, str]] = []
        self.translated_chunks: List[Optional[str]] = []
        self._chunk_to_paragraph_ranges: List[tuple[int, int]] = []

    async def prepare_for_translation(self) -> bool:
        try:
            extracted = extract_pdf_text(str(self.input_file_path))
            self.paragraphs = list(extracted.paragraphs)
            full_text = paragraphs_to_chunk_text(self.paragraphs)

            from src.core.text_processor import split_text_into_chunks

            self.chunks = split_text_into_chunks(
                text=full_text,
                max_tokens_per_chunk=self.config.get("max_tokens_per_chunk"),
                soft_limit_ratio=self.config.get("soft_limit_ratio"),
            )
            self.translated_chunks = [None] * len(self.chunks)
            return True
        except PdfExtractionError:
            return False
        except Exception:
            return False

    def get_translation_units(self) -> List[TranslationUnit]:
        units = []
        for i, chunk in enumerate(self.chunks):
            units.append(
                TranslationUnit(
                    unit_id=f"chunk_{i}",
                    content=chunk["main_content"],
                    context_before=chunk.get("context_before", ""),
                    context_after=chunk.get("context_after", ""),
                    metadata={"chunk_index": i, "total_chunks": len(self.chunks)},
                )
            )
        return units

    async def save_unit_translation(self, unit_id: str, translated_content: str) -> bool:
        try:
            chunk_index = int(unit_id.split("_")[1])
            if 0 <= chunk_index < len(self.translated_chunks):
                self.translated_chunks[chunk_index] = translated_content
                return True
            return False
        except Exception:
            return False

    def _rebuild_paragraphs(self, bilingual: bool = False) -> List[str]:
        """Merge translated chunks back into paragraph blocks."""
        text_chunks: List[str] = []
        separator = "─" * 40

        for i, translated_chunk in enumerate(self.translated_chunks):
            original = self.chunks[i]["main_content"].strip()
            translated = translated_chunk.strip() if translated_chunk else original
            if bilingual:
                text_chunks.append(f"{original}\n\n{translated}\n\n{separator}")
            else:
                text_chunks.append(translated if translated_chunk else original)

        joiner = "\n\n" if bilingual else "\n"
        merged = joiner.join(text_chunks)
        if bilingual and merged.endswith(separator):
            merged = merged[: -len(separator)].rstrip()

        paragraphs = [p.strip() for p in merged.split("\n\n") if p.strip()]
        return paragraphs or self.paragraphs

    async def reconstruct_output(self, bilingual: bool = False) -> bytes:
        paragraphs = self._rebuild_paragraphs(bilingual=bilingual)
        output_path = Path(self.output_file_path)
        ext = self.config.get("pdf_output_extension") or output_path.suffix
        write_translated_output(paragraphs, output_path, output_extension=ext)

        # Return bytes for API consumers that expect in-memory output.
        return output_path.read_bytes()

    async def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> int:
        try:
            chunks_data = checkpoint_data.get("chunks", [])
            for chunk_data in chunks_data:
                if chunk_data.get("status") == "completed":
                    metadata = chunk_data.get("chunk_data", {})
                    chunk_index = metadata.get("chunk_index")
                    translated_text = chunk_data.get("translated_text")
                    if chunk_index is not None and translated_text is not None:
                        if 0 <= chunk_index < len(self.translated_chunks):
                            self.translated_chunks[chunk_index] = translated_text
            return checkpoint_data.get("resume_from_index", 0)
        except Exception:
            return 0

    async def cleanup(self):
        pass

    @property
    def format_name(self) -> str:
        return "pdf"

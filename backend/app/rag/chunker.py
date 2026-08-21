import re
from dataclasses import dataclass

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")
_WHITESPACE = re.compile(r"[ \t]+")


@dataclass(frozen=True, slots=True)
class PageText:
    page: int
    text: str

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page numbers are one-based")


@dataclass(frozen=True, slots=True)
class TextChunk:
    page: int
    chunk_index: int
    text: str


class DocumentChunker:
    """Creates page-aware chunks while favoring paragraph boundaries."""

    def __init__(self, *, max_chars: int = 1800, overlap_chars: int = 220) -> None:
        if max_chars < 200:
            raise ValueError("max_chars must be at least 200")
        if not 0 <= overlap_chars < max_chars:
            raise ValueError("overlap_chars must be non-negative and smaller than max_chars")
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars

    def chunk(self, pages: list[PageText]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for page in pages:
            units = self._paragraph_units(page.text)
            page_chunks = self._pack_units(units)
            for text in page_chunks:
                chunks.append(TextChunk(page=page.page, chunk_index=len(chunks), text=text))
        return chunks

    def _paragraph_units(self, text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        paragraphs = [
            self._normalize_paragraph(value) for value in _PARAGRAPH_BREAK.split(normalized)
        ]
        units: list[str] = []
        for paragraph in paragraphs:
            if not paragraph:
                continue
            units.extend(self._split_oversized_paragraph(paragraph))
        return units

    @staticmethod
    def _normalize_paragraph(paragraph: str) -> str:
        lines = [_WHITESPACE.sub(" ", line.strip()) for line in paragraph.splitlines()]
        return " ".join(line for line in lines if line)

    def _split_oversized_paragraph(self, paragraph: str) -> list[str]:
        if len(paragraph) <= self._max_chars:
            return [paragraph]

        words = paragraph.split()
        parts: list[str] = []
        current: list[str] = []
        current_length = 0
        for word in words:
            next_length = current_length + len(word) + (1 if current else 0)
            if current and next_length > self._max_chars:
                parts.append(" ".join(current))
                current = [word]
                current_length = len(word)
            else:
                current.append(word)
                current_length = next_length
        if current:
            parts.append(" ".join(current))
        return parts

    def _pack_units(self, units: list[str]) -> list[str]:
        if not units:
            return []

        chunks: list[str] = []
        current: list[str] = []
        for unit in units:
            candidate = "\n\n".join([*current, unit])
            if current and len(candidate) > self._max_chars:
                chunks.append("\n\n".join(current))
                current = self._overlap_units(current)
                while current and len("\n\n".join([*current, unit])) > self._max_chars:
                    current.pop(0)
            current.append(unit)
        if current:
            final_chunk = "\n\n".join(current)
            if not chunks or final_chunk != chunks[-1]:
                chunks.append(final_chunk)
        return chunks

    def _overlap_units(self, units: list[str]) -> list[str]:
        if self._overlap_chars == 0:
            return []
        overlap: list[str] = []
        length = 0
        for unit in reversed(units):
            candidate_length = length + len(unit) + (2 if overlap else 0)
            if overlap and candidate_length > self._overlap_chars:
                break
            overlap.insert(0, unit)
            length = candidate_length
            if length >= self._overlap_chars:
                break
        return overlap

from typing import Protocol

import pymupdf

from app.rag.chunker import ExtractionMethod, PageText


class PDFExtractionError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PageOCR(Protocol):
    def extract(self, page: pymupdf.Page) -> str: ...


class PyMuPDFTesseractOCR:
    def __init__(self, *, languages: str, dpi: int) -> None:
        self._languages = languages
        self._dpi = dpi

    def extract(self, page: pymupdf.Page) -> str:
        try:
            text_page = page.get_textpage_ocr(
                language=self._languages,
                dpi=self._dpi,
                full=True,
            )
            return _normalize(page.get_text("text", sort=True, textpage=text_page))
        except (RuntimeError, ValueError) as exc:
            raise PDFExtractionError("OCR_UNAVAILABLE") from exc


class PyMuPDFExtractor:
    def __init__(
        self,
        *,
        max_pages: int,
        ocr: PageOCR | None = None,
        min_native_chars: int = 1,
        max_ocr_pages: int = 100,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        if min_native_chars < 0:
            raise ValueError("min_native_chars cannot be negative")
        if max_ocr_pages < 1:
            raise ValueError("max_ocr_pages must be positive")
        self._max_pages = max_pages
        self._ocr = ocr
        self._min_native_chars = min_native_chars
        self._max_ocr_pages = max_ocr_pages

    def extract(self, pdf_bytes: bytes) -> list[PageText]:
        if not pdf_bytes:
            raise PDFExtractionError("PDF_EMPTY")
        try:
            with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
                if document.needs_pass:
                    raise PDFExtractionError("PDF_PASSWORD_PROTECTED")
                if document.page_count < 1:
                    raise PDFExtractionError("PDF_EMPTY")
                if document.page_count > self._max_pages:
                    raise PDFExtractionError("PDF_PAGE_LIMIT_EXCEEDED")
                pages: list[PageText] = []
                ocr_page_count = 0
                for index in range(document.page_count):
                    page = document.load_page(index)
                    native_text = _normalize(page.get_text("text", sort=True))
                    if len(native_text) >= self._min_native_chars or self._ocr is None:
                        pages.append(
                            PageText(
                                page=index + 1,
                                text=native_text,
                                extraction_method=(
                                    ExtractionMethod.NATIVE
                                    if native_text
                                    else ExtractionMethod.NONE
                                ),
                            )
                        )
                        continue
                    ocr_page_count += 1
                    if ocr_page_count > self._max_ocr_pages:
                        raise PDFExtractionError("PDF_OCR_PAGE_LIMIT_EXCEEDED")
                    ocr_text = self._ocr.extract(page)
                    pages.append(
                        PageText(
                            page=index + 1,
                            text=ocr_text,
                            extraction_method=(
                                ExtractionMethod.OCR if ocr_text else ExtractionMethod.NONE
                            ),
                        )
                    )
        except PDFExtractionError:
            raise
        except (RuntimeError, ValueError, pymupdf.FileDataError) as exc:
            raise PDFExtractionError("PDF_EXTRACTION_FAILED") from exc
        if not any(page.text for page in pages):
            raise PDFExtractionError("PDF_NO_EXTRACTABLE_TEXT")
        return pages


def _normalize(text: str) -> str:
    return text.replace("\x00", "").strip()

import pymupdf

from app.rag.chunker import PageText


class PDFExtractionError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PyMuPDFExtractor:
    def __init__(self, *, max_pages: int) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        self._max_pages = max_pages

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
                pages = [
                    PageText(
                        page=index + 1,
                        text=document.load_page(index)
                        .get_text("text", sort=True)
                        .replace("\x00", "")
                        .strip(),
                    )
                    for index in range(document.page_count)
                ]
        except PDFExtractionError:
            raise
        except (RuntimeError, ValueError, pymupdf.FileDataError) as exc:
            raise PDFExtractionError("PDF_EXTRACTION_FAILED") from exc
        if not any(page.text for page in pages):
            raise PDFExtractionError("PDF_NO_EXTRACTABLE_TEXT")
        return pages

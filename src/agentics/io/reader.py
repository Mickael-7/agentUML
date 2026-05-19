from __future__ import annotations

from pathlib import Path


class UnsupportedFormatError(Exception):
    pass


_SUPPORTED = {".md", ".txt", ".pdf", ".docx"}


class DocumentReader:
    def read(self, path: str) -> str:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix not in _SUPPORTED:
            raise UnsupportedFormatError(
                f"Unsupported file format '{suffix}'. "
                f"Accepted formats: {', '.join(sorted(_SUPPORTED))}"
            )
        if suffix in {".md", ".txt"}:
            return p.read_text(encoding="utf-8")
        if suffix == ".pdf":
            return self._read_pdf(p)
        if suffix == ".docx":
            return self._read_docx(p)

    def _read_pdf(self, path: Path) -> str:
        import pdfplumber

        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)

    def _read_docx(self, path: Path) -> str:
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text)

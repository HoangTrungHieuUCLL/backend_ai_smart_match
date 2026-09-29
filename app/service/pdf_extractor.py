from __future__ import annotations

import io

import fitz
import pytesseract
from PIL import Image


try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
except Exception:  # pragma: no cover - optional dependency
    DocumentFile = None
    ocr_predictor = None


class PDFTextExtractor:
    _doctr_predictor = None

    def extract_from_path(self, pdf_path) -> str:
        with open(pdf_path, "rb") as handle:
            file_bytes = handle.read()

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = self._extract_doc(doc, file_bytes=file_bytes)
        doc.close()
        return text

    def extract_from_bytes(self, file_bytes: bytes) -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = self._extract_doc(doc, file_bytes=file_bytes)
        doc.close()
        return text

    def _extract_doc(self, doc, file_bytes: bytes | None = None):
        if file_bytes is not None and self._can_use_doctr() and len(doc) > 0:
            first_page_text = self._extract_structured_page_text(doc[0])
            if not first_page_text:
                doctr_text = self._extract_with_doctr(file_bytes)
                if doctr_text:
                    return doctr_text

        text_parts = []

        for page in doc:
            page_text = self._extract_page_text(page)
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts).strip()

    def _extract_page_text(self, page) -> str:
        structured_text = self._extract_structured_page_text(page)
        if structured_text:
            return structured_text

        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img).strip()

    def _extract_structured_page_text(self, page) -> str:
        blocks = []

        for block in page.get_text("blocks", sort=True):
            if len(block) < 5:
                continue

            x0, y0, x1, y1, text = block[:5]
            block_text = self._normalize_block_text(text)
            if not block_text:
                continue

            blocks.append((float(x0), float(y0), float(x1), float(y1), block_text))

        if not blocks:
            return ""

        page_width = float(page.rect.width)
        if self._looks_like_two_column_layout(blocks, page_width):
            left_column = sorted((block for block in blocks if block[0] <= page_width / 2), key=lambda item: (item[1], item[0]))
            right_column = sorted((block for block in blocks if block[0] > page_width / 2), key=lambda item: (item[1], item[0]))
            ordered_blocks = left_column + right_column
        else:
            ordered_blocks = sorted(blocks, key=lambda item: (item[1], item[0]))

        return "\n\n".join(block_text for _, _, _, _, block_text in ordered_blocks).strip()

    def _looks_like_two_column_layout(self, blocks, page_width: float) -> bool:
        if len(blocks) < 4:
            return False

        left_blocks = sum(1 for block in blocks if block[0] <= page_width / 2)
        right_blocks = len(blocks) - left_blocks
        return left_blocks >= 2 and right_blocks >= 2

    @staticmethod
    def _normalize_block_text(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines).strip()

    @classmethod
    def _get_doctr_predictor(cls):
        if cls._doctr_predictor is None and ocr_predictor is not None:
            cls._doctr_predictor = ocr_predictor(pretrained=True)

        return cls._doctr_predictor

    def _can_use_doctr(self) -> bool:
        return DocumentFile is not None and ocr_predictor is not None

    def _extract_with_doctr(self, pdf_stream) -> str:
        predictor = self._get_doctr_predictor()
        if predictor is None:
            return ""

        document = DocumentFile.from_pdf(pdf_stream)
        result = predictor(document)
        page_text_parts: list[str] = []

        for page in result.pages:
            block_parts: list[str] = []
            for block in page.blocks:
                line_parts: list[str] = []
                for line in block.lines:
                    word_text = " ".join(word.value for word in line.words).strip()
                    if word_text:
                        line_parts.append(word_text)
                block_text = "\n".join(line_parts).strip()
                if block_text:
                    block_parts.append(block_text)

            page_text = "\n\n".join(block_parts).strip()
            if page_text:
                page_text_parts.append(page_text)

        return "\n\n".join(page_text_parts).strip()
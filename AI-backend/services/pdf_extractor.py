# services/pdf_extractor.py

import fitz
import pytesseract
from PIL import Image
import io


class PDFTextExtractor:

    def extract_from_path(self, pdf_path) -> str:
        return self._extract(pdf_path)

    def extract_from_bytes(self, file_bytes: bytes) -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = self._extract_doc(doc)
        doc.close()
        return text

    def _extract(self, pdf_path):
        doc = fitz.open(pdf_path)
        text = self._extract_doc(doc)
        doc.close()
        return text

    def _extract_doc(self, doc):
        text_parts = []

        for page in doc:
            page_text = page.get_text("text")

            # fallback OCR if needed
            if not page_text.strip():
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(img)

            text_parts.append(page_text)

        return "\n".join(text_parts).strip()
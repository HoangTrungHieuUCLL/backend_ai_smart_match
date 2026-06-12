from __future__ import annotations

from typing import List, Tuple

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


def extract_words_and_boxes_from_pdf_bytes(file_bytes: bytes) -> List[dict]:
    """Extract word-level text and bounding boxes from PDF bytes.

    Returns a list of pages. Each page is a dict:
      {"width": float, "height": float, "words": [(text, (x0,y0,x1,y1)), ...]}

    If PyMuPDF (`fitz`) is not available, raises RuntimeError.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF box extraction")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        width = float(page.rect.width)
        height = float(page.rect.height)
        raw_words = []
        # page.get_text("words") returns tuples: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        for w in page.get_text("words"):
            x0, y0, x1, y1, text = float(w[0]), float(w[1]), float(w[2]), float(w[3]), w[4]
            raw_words.append({"text": text, "bbox": (x0, y0, x1, y1)})

        # Extract blocks and associate words to blocks by bbox overlap
        blocks = []
        for b in page.get_text("blocks"):
            # block tuple: (x0, y0, x1, y1, text, block_no)
            bx0, by0, bx1, by1, btext = float(b[0]), float(b[1]), float(b[2]), float(b[3]), b[4]
            block_words = []
            for w in raw_words:
                x0, y0, x1, y1 = w["bbox"]
                # check if word center lies within block bbox
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                if bx0 - 1e-3 <= cx <= bx1 + 1e-3 and by0 - 1e-3 <= cy <= by1 + 1e-3:
                    block_words.append(w)

            blocks.append({
                "text": btext.strip(),
                "bbox": (bx0, by0, bx1, by1),
                "words": block_words,
                "page_width": width,
                "page_height": height,
            })

        pages.append({"width": width, "height": height, "words": raw_words, "blocks": blocks})

    doc.close()
    return pages


def normalize_bbox_for_layoutlm(box: Tuple[float, float, float, float], page_width: float, page_height: float) -> List[int]:
    """Normalize a bbox to LayoutLM integer coordinates (0..1000).

    LayoutLM expects bbox as [x0, y0, x1, y1] with integers in [0,1000].
    """
    x0, y0, x1, y1 = box
    def norm_x(x):
        return int(max(0, min(1000, round((x / page_width) * 1000))))

    def norm_y(y):
        return int(max(0, min(1000, round((y / page_height) * 1000))))

    return [norm_x(x0), norm_y(y0), norm_x(x1), norm_y(y1)]

#!/usr/bin/env python3
"""Smoke test for the PDF word+box extractor.

Creates a small synthetic PDF in-memory, runs the extractor
`app.service.layoutlm_pdf_processor.extract_words_and_boxes_from_pdf_bytes`
and prints a concise summary of the extracted pages, blocks and sample words.

Usage:
    python scripts/run_layoutlm_smoke.py

Dependencies:
    pip install PyMuPDF
"""

from app.service.layoutlm_pdf_processor import extract_words_and_boxes_from_pdf_bytes, normalize_bbox_for_layoutlm
import fitz


def make_sample_pdf_bytes():
    doc = fitz.open()
    p1 = doc.new_page()
    text1 = """
John Doe
Senior Software Engineer
Email: john.doe@example.com
Phone: +84 123 456 789

Skills
Python, FastAPI, SQL, Docker

Experience
Company A - Software Engineer (2020 - 2023)
- Built APIs
- Worked on data pipelines
"""
    p1.insert_text((72, 72), text1, fontsize=11)

    p2 = doc.new_page()
    text2 = """
Education
University of Somewhere - BSc Computer Science (2016 - 2020)

Projects
Project X: An ML project using Python and scikit-learn
"""
    p2.insert_text((72, 72), text2, fontsize=11)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def run():
    pdf_bytes = make_sample_pdf_bytes()
    pages = extract_words_and_boxes_from_pdf_bytes(pdf_bytes)

    print('pages_count=', len(pages))
    for i, p in enumerate(pages):
        print(f"--- page {i+1} (w={p['width']}, h={p['height']})")
        print('blocks_count=', len(p.get('blocks', [])))
        for bi, b in enumerate(p.get('blocks', [])[:5]):
            print(f" block {bi}: text_preview={repr(b['text'][:120])}")
            words = b.get('words', [])[:10]
            print('  words_count=', len(b.get('words', [])))
            print('  sample_words=')
            for w in words:
                print('   ', w['text'], '--', normalize_bbox_for_layoutlm(w['bbox'], p['width'], p['height']))


if __name__ == '__main__':
    run()

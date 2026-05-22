from pathlib import Path
import csv
import fitz
import pytesseract
from PIL import Image
import io
from app.service.pdf_extractor import PDFTextExtractor

BASE_DIRECTORY = Path(__file__).resolve().parent.parent
DATASET_DIRECTORY = BASE_DIRECTORY / "cv-dataset"

CATEGORY = "test"

RAW_DIRECTORY = (
    DATASET_DIRECTORY
    / "raw"
    /"test"
)

TEXT_DIRECTORY = DATASET_DIRECTORY / "extracted_text" / CATEGORY
METADATA_DIRECTORY = DATASET_DIRECTORY / "metadata"
METADATA_FILE = METADATA_DIRECTORY / f"cv_metadata_{CATEGORY.lower().replace(' ', '_')}.csv"

TEXT_DIRECTORY.mkdir(parents=True, exist_ok=True)
METADATA_DIRECTORY.mkdir(parents=True, exist_ok=True)


def extract_rawtext_from_pdf(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)
    text_parts = []

    for page in document:
        text_parts.append(page.get_text("text"))

    document.close()
    return "\n".join(text_parts).strip()


def extract_text_with_ocr(pdf_path: Path) -> str:
    document = fitz.open(pdf_path)
    text_parts = []

    for page_number, page in enumerate(document, start=1):
        pix = page.get_pixmap(dpi=200)
        image_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(image_bytes))

        page_text = pytesseract.image_to_string(image)
        text_parts.append(page_text)

    document.close()
    return "\n".join(text_parts).strip()


def extract_text_with_fallback(pdf_path: Path) -> tuple[str, str]:
    pymupdf_text = extract_rawtext_from_pdf(pdf_path)

    if len(pymupdf_text.strip()) > 0:
        return pymupdf_text, "pymupdf"

    ocr_text = extract_text_with_ocr(pdf_path)

    if len(ocr_text.strip()) > 0:
        return ocr_text, "ocr"

    return "", "empty"


def main():
    pdf_files = list(RAW_DIRECTORY.rglob("*.pdf"))
    metadata_rows = []

    if not pdf_files:
        print(f"No PDF files found in: {RAW_DIRECTORY}")
        return

    print(f"Processing category: {CATEGORY}")
    print(f"Found {len(pdf_files)} PDF files.")

    for index, pdf_path in enumerate(pdf_files, start=1):
        cv_id = f"CV{index:04d}"
        text_output_path = TEXT_DIRECTORY / f"{cv_id}.txt"

        status = "success"
        error = ""
        extraction_method = "unknown"
        extracted_text = ""
        text_length = 0

        try:
            extractor = PDFTextExtractor()
            extracted_text = extractor.extract_from_path(pdf_path)
            extraction_method = "pymupdf+ocr"
            
            text_length = len(extracted_text.strip())

            if text_length == 0:
                status = "empty_text"
            elif text_length < 500:
                status = "low_quality"
            else:
                status = "success"
            if text_length > 0:
                text_output_path.write_text(extracted_text, encoding="utf-8")
                
        except Exception as e:
            status = "failed"
            error = str(e)
            text_length = 0

        metadata_rows.append({
            "cv_id": cv_id,
            "category": CATEGORY,
            "original_filename": pdf_path.name,
            "source_folder": str(pdf_path.parent),
            "text_path": str(text_output_path),
            "text_length": text_length,
            "extraction_method": extraction_method,
            "status": status,
            "error": error
        })

        print(
            f"{cv_id}: {pdf_path.name} -> {status} "
            f"| method={extraction_method} "
            f"| text_length={text_length}"
        )

    with METADATA_FILE.open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "cv_id",
            "category",
            "original_filename",
            "source_folder",
            "text_path",
            "text_length",
            "extraction_method",
            "status",
            "error"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"\nProcessed {len(metadata_rows)} PDF files.")
    print(f"Metadata saved to: {METADATA_FILE}")


if __name__ == "__main__":
    main()
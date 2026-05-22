# from services.parser import CVParser
# from utils.text_cleaning import TextCleaner
import fitz
import io
# class CVPipeline:

#     def __init__(self):
#         self.cleaner = TextCleaner()
#         self.parser = CVParser()

#     def run(self, text: str):
#         cleaned_text = self.cleaner.clean(text)
#         return self.parser.parse(cleaned_text)

# pipelines/cv_pipeline.py

class CVPipeline:

    def extract_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        text_parts = []
        for page in doc:
            text_parts.append(page.get_text("text"))

        doc.close()
        return "\n".join(text_parts).strip()
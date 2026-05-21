from fastapi import FastAPI, UploadFile, File
from utils.text_cleaning import TextCleaner
from services.gemini_cv_service import GeminiCVService
from pipelines.cv_pipeline import CVPipeline
from services.pdf_extractor import PDFTextExtractor

# app = FastAPI()

# pipeline = CVPipeline()
# cleaner = TextCleaner()
# gemini_service = GeminiCVService()

# @app.post("/parse-cv")
# async def parse_cv(file: UploadFile = File(...)):
#     content = await file.read()
#     raw_text = content.decode("utf-8", errors="ignore")
#     cleaned_text = cleaner.clean(raw_text)
    
#     result = pipeline.run(cleaned_text)

#     # response = {
#     #     "name": result.name,
#     #     "email": result.email,
#     #     "skills": result.skills,
#     #     "experience": result.experience,
#     #     "education": result.education
#     # }

#     # return response
#     return result.model_dump()




app = FastAPI()

pipeline = CVPipeline()
cleaner = TextCleaner()
gemini_service = GeminiCVService()


# @app.post("/parse-cv")
# async def parse_cv(file: UploadFile = File(...)):
#     content = await file.read()
#     raw_text = pipeline.extract_from_bytes(content, file.filename)

#     cleaned_text = cleaner.clean(raw_text)
#     structured_cv = gemini_service.parse_cv(cleaned_text)
#     return structured_cv.model_dump()


extractor = PDFTextExtractor()


@app.post("/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    content = await file.read()

    raw_text = extractor.extract_from_bytes(content)

    cleaned_text = cleaner.clean(raw_text)

    structured_cv = gemini_service.parse_cv(cleaned_text)

    return structured_cv.model_dump()
from fastapi import APIRouter, Depends, UploadFile, File, Form, FastAPI
from sqlalchemy.orm import Session

from app.ai.pipelines.cv_pipeline import CVPipeline
from app.database import SessionLocal
from app.service.cv import CVService
import httpx

from app.models.cv import CV
from app.service.gemini_cv_service import GeminiCVService
from app.service.job import JobService
from app.service.pdf_extractor import PDFTextExtractor
from app.utils.text_cleaning import TextCleaner

app = FastAPI()
router = APIRouter()
service = CVService()
job_service = JobService()
pipeline = CVPipeline()
cleaner = TextCleaner()
gemini_service = GeminiCVService()
extractor = PDFTextExtractor()

AI_URL = "http://localhost:8000/parse-cv"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/parse-cv")
async def upload_cv(
    cv: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_bytes = await cv.read()

    # extract raw text from file bytes
    raw_text = extractor.extract_from_bytes(file_bytes)

    # clean extracted text
    cleaned_text = cleaner.clean(raw_text)

    # structured CV parsing via AI service
    structured_cv = gemini_service.parse_cv(cleaned_text)

    return {
        "message": "CV processed",
        "ai_result": structured_cv.model_dump()
    }
    # scores = job_service.assign_placeholder_compatability_scores(db)

    # return scores

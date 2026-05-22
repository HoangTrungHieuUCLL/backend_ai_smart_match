from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService
from app.service.gemini_cv_service import GeminiCVService
from app.service.job import JobService
from app.service.pdf_extractor import PDFTextExtractor
from app.utils.text_cleaning import TextCleaner

router = APIRouter()
service = CVService()
job_service = JobService()
cleaner = TextCleaner()
gemini_service = GeminiCVService()
extractor = PDFTextExtractor()


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

    raw_text = extractor.extract_from_bytes(file_bytes)
    cleaned_text = cleaner.clean(raw_text)

    try:
        parsed_cv = gemini_service.parse_cv(cleaned_text)
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail={"message": "AI service failed to parse CV", "error": str(e)},
        )

    # dict for DB, json string for response
    ai_result_dict = parsed_cv.model_dump()
    ai_result_json = parsed_cv.model_dump_json()

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=cv.filename or "uploaded_cv.pdf",
            structured_data=ai_result_dict,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"AI result was parsed, but saving to database failed: {exc}",
        ) from exc

    return {
        "message": "CV processed and saved",
        "cv_id": profile.cv_id,
        "profile_id": profile.id,
        "ai_result": ai_result_json,
    }
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService
from app.service.gemini_cv_service import GeminiCVService
from app.service.job import JobService
from app.service.local_cv_parser_service import LocalCVParserService
from app.service.pdf_extractor import PDFTextExtractor
from app.utils.text_cleaning import TextCleaner
from app.service.cv_embedding_service import embed_skills

router = APIRouter()
service = CVService()
job_service = JobService()
cleaner = TextCleaner()
gemini_service = GeminiCVService()
local_parser_service = LocalCVParserService()
extractor = PDFTextExtractor()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _prepare_ai_result_with_skills_embedding(
    parsed_cv,
    *,
    given_name: str | None = None,
    middle_name: str | None = None,
    family_name: str | None = None,
    email: str | None = None,
) -> dict:
    ai_result_dict = parsed_cv.model_dump()
    candidate_profile = ai_result_dict.setdefault("candidate_profile", {})

    if given_name is not None:
        candidate_profile["given_name"] = given_name
    if middle_name is not None:
        candidate_profile["middle_name"] = middle_name
    if family_name is not None:
        candidate_profile["family_name"] = family_name
    if email is not None:
        candidate_profile["email"] = email

    skills = candidate_profile.get("skills") or []
    ai_result_dict["skills_embedding"] = embed_skills(skills)

    return ai_result_dict


async def _parse_uploaded_cv(cv: UploadFile):
    file_bytes = await cv.read()

    raw_text = extractor.extract_from_bytes(file_bytes)
    cleaned_text = cleaner.clean(raw_text)

    try:
        return gemini_service.parse_cv(cleaned_text)
    except ValueError:
        return local_parser_service.parse_cv(cleaned_text)


@router.post("/parse-cv")
async def parse_cv(
    cv: UploadFile = File(...),
    given_name: str | None = Form(None),
    middle_name: str | None = Form(None),
    family_name: str | None = Form(None),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
):
    parsed_cv = await _parse_uploaded_cv(cv)

    ai_result_dict = _prepare_ai_result_with_skills_embedding(
        parsed_cv,
        given_name=given_name,
        middle_name=middle_name,
        family_name=family_name,
        email=email,
    )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=cv.filename or "uploaded_cv.pdf",
            structured_data=ai_result_dict,
            compatibility_scores=None,
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
        "ai_result": ai_result_dict,
    }


@router.get("/profiles/{profile_id}/all")
def calculate_all_compatibility_scores_for_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    result = job_service.calculate_and_save_scores_for_profile(
        db,
        profile_id,
    )

    return result

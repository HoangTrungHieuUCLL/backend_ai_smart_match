from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService
from app.service.gemini_cv_service import GeminiCVService
from app.service.job import JobService
from app.service.pdf_extractor import PDFTextExtractor
from app.utils.text_cleaning import TextCleaner
from app.service.cv_embedding_service import embed_skills

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
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail={"message": "AI service failed to parse CV", "error": str(e)},
        ) from e

@router.post("/cv/upload")
async def upload_cv_with_form_data(
        familyName: str = Form(...),
        middleName: str = Form(None),
        givenName: str = Form(...),
        email: str = Form(...),
        cv: UploadFile = File(...),
        db: Session = Depends(get_db)
):
        parsed_cv = await _parse_uploaded_cv(cv)
        ai_result_dict = _prepare_ai_result_with_skills_embedding(
            parsed_cv,
            given_name=givenName,
            middle_name=middleName,
            family_name=familyName,
            email=email,
        )

        top_10_scores = job_service.calculate_top_compatibility_scores(
            db,
            ai_result_dict.get("skills_embedding"),
        )

        try:
            profile = service.save_ai_cv_result(
                db,
                filename=cv.filename or "uploaded_cv.pdf",
                structured_data=ai_result_dict,
                compatibility_scores=top_10_scores,
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
            "top_10_compatibility_scores": top_10_scores,
            "ai_result": ai_result_dict,
        }


@router.post("/parse-cv")
async def parse_cv(
    cv: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    parsed_cv = await _parse_uploaded_cv(cv)
    ai_result_dict = _prepare_ai_result_with_skills_embedding(parsed_cv)

    top_10_scores = job_service.calculate_top_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
    )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=cv.filename or "uploaded_cv.pdf",
            structured_data=ai_result_dict,
            compatibility_scores=top_10_scores,
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
        "top_10_compatibility_scores": top_10_scores,
        "ai_result": ai_result_dict,
    }

@router.post("/test-compatibility-score")
def test_compatibility_score(db: Session = Depends(get_db)):
    fake_ai_result = {
        "candidate_profile": {
            "given_name": "Test",
            "middle_name": None,
            "family_name": "Candidate",
            "current_title": "Backend Developer",
            "skills": ["Python", "FastAPI", "SQL", "Docker", "Machine Learning"],
            "phone": "0000000000",
            "location": "Leuven",
            "email": "test@example.com",
        },
        "work_experiences": [],
        "educations": [],
        "projects": [],
        "languages": [],
    }

    fake_ai_result["skills_embedding"] = embed_skills(
        fake_ai_result["candidate_profile"]["skills"]
    )

    top_10_scores = job_service.calculate_top_compatibility_scores(
        db,
        fake_ai_result.get("skills_embedding"),
    )

    profile = service.save_ai_cv_result(
        db,
        filename="test-cv-without-gemini.pdf",
        structured_data=fake_ai_result,
        compatibility_scores=top_10_scores,
    )

    return {
        "message": "Compatibility score test completed without Gemini",
        "profile_id": profile.id,
        "cv_id": profile.cv_id,
        "top_10_compatibility_scores": top_10_scores,
    }
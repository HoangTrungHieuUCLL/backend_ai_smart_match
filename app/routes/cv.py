from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService
from app.service.cv_embedding_service import embed_skills
from app.service.gemini_cv_service import GeminiCVService
from app.service.job import JobService
from app.service.pdf_extractor import PDFTextExtractor
from app.utils.cv_filename import build_cv_filename
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


def _skills_as_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return [str(value).strip()] if str(value).strip() else []


def _normalise_edited_cv_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    candidate_profile = data.get("candidate_profile")

    if not isinstance(candidate_profile, dict):
        candidate_profile = {}
        data["candidate_profile"] = candidate_profile

    for nested_key, canonical_key in (
        ("work_experiences", "work_experience"),
        ("educations", "education"),
        ("projects", "projects"),
        ("languages", "languages"),
        ("certifications", "certifications"),
    ):
        if canonical_key not in data and nested_key in candidate_profile:
            data[canonical_key] = candidate_profile.get(nested_key)

    skills = _skills_as_list(candidate_profile.get("skills"))
    candidate_profile["skills"] = skills
    data["skills_embedding"] = embed_skills(skills)

    return data


def _prepare_ai_result_with_skills_embedding(
    parsed_cv,
    *,
    given_name: str | None = None,
    middle_name: str | None = None,
    family_name: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    ai_result_dict = parsed_cv.model_dump()
    candidate_profile = ai_result_dict.get("candidate_profile")

    if not isinstance(candidate_profile, dict):
        candidate_profile = {}
        ai_result_dict["candidate_profile"] = candidate_profile

    if given_name is not None:
        candidate_profile["given_name"] = given_name
    if middle_name is not None:
        candidate_profile["middle_name"] = middle_name
    if family_name is not None:
        candidate_profile["family_name"] = family_name
    if email is not None:
        candidate_profile["email"] = email

    skills = _skills_as_list(candidate_profile.get("skills"))
    candidate_profile["skills"] = skills
    ai_result_dict["skills_embedding"] = embed_skills(skills)

    return ai_result_dict


async def _parse_uploaded_cv(cv: UploadFile):
    file_bytes = await cv.read()

    raw_text = extractor.extract_from_bytes(file_bytes)
    cleaned_text = cleaner.clean(raw_text)

    try:
        return gemini_service.parse_cv(cleaned_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI service failed to parse CV",
                "error": str(exc),
            },
        ) from exc


@router.post("/cv/upload")
async def upload_cv_with_form_data(
    givenName: str = Form(...),
    middleName: str | None = Form(None),
    familyName: str = Form(...),
    email: str = Form(...),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    parsed_cv = await _parse_uploaded_cv(cv)

    ai_result_dict = _prepare_ai_result_with_skills_embedding(
        parsed_cv,
        given_name=givenName,
        middle_name=middleName,
        family_name=familyName,
        email=email,
    )

    normalized_filename = build_cv_filename(
        given_name=givenName,
        middle_name=middleName,
        family_name=familyName,
    )
    top_10_scores = job_service.calculate_top_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
        limit=10,
    )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=normalized_filename,
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


@router.put("/cv/{profile_id}/extracted-data")
async def update_extracted_cv_data(
    profile_id: int,
    cv_data: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    structured_data = _normalise_edited_cv_payload(cv_data)

    try:
        profile = service.update_ai_cv_result(
            db,
            profile_id=profile_id,
            structured_data=structured_data,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Edited CV data could not be saved: {exc}",
        ) from exc

    if profile is None:
        raise HTTPException(status_code=404, detail="CV profile not found")

    response_data = dict(structured_data)
    response_data.pop("skills_embedding", None)

    return {
        "message": "CV data updated",
        "cv_id": profile.cv_id,
        "profile_id": profile.id,
        "ai_result": response_data,
    }


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
    top_10_scores = job_service.calculate_top_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
        limit=10,
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


@router.get("/profiles/{profile_id}/all")
def calculate_all_compatibility_scores_for_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    return job_service.calculate_and_save_scores_for_profile(db, profile_id)

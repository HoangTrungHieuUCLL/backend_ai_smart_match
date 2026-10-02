import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.cv import CompatibilityScore, Profile
from app.service.bert_cv_classifier import get_bert_classifier
from app.service.auth import auth_service, security
from app.service.cv import CVService
from app.service.cv_embedding_service import embed_skills
from app.service.cv_parsing_service import CVParsingService
from app.service.job import JobService
from app.service.pdf_extractor import PDFTextExtractor
from app.service.layoutlm_pdf_processor import extract_words_and_boxes_from_pdf_bytes
from app.service.skill_taxonomy import canonical_skill_labels
from app.utils.cv_filename import build_cv_filename
from app.utils.text_cleaning import TextCleaner

logger = logging.getLogger(__name__)
_CANONICAL_SKILLS = frozenset(canonical_skill_labels())

router = APIRouter()
service = CVService()
job_service = JobService()
cleaner = TextCleaner()
cv_parser_service = CVParsingService()
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


async def _parse_uploaded_cv(cv: UploadFile) -> tuple[Any, list[dict]]:
    """
    Extract text from the uploaded PDF, then:
    1. Structure the CV with the heuristic CVParsingService.
    2. Replace its skills with the fine-tuned DistilBERT skills, filtered to
       the canonical skill taxonomy.
    Returns (CVParsed, classified_tokens).
    classified_tokens is a list of {"word": str, "label": str} dicts that the
    frontend can render as an annotated word-level view for user review.
    Keeps the heuristic skills if the BERT model is unavailable.
    The CPU-bound work (PDF/OCR extraction, BERT inference) runs in a worker
    thread so it doesn't block the event loop for other requests.
    """
    file_bytes = await cv.read()
    return await run_in_threadpool(_parse_cv_bytes_sync, file_bytes)


def _parse_cv_bytes_sync(file_bytes: bytes) -> tuple[Any, list[dict]]:
    raw_text = extractor.extract_from_bytes(file_bytes)
    cleaned_text = cleaner.clean(raw_text)

    # --- Heuristic parser: profile, experience, education, ... ----------
    pages = None
    try:
        pages = extract_words_and_boxes_from_pdf_bytes(file_bytes)
    except Exception:
        pages = None

    try:
        parsed_cv = cv_parser_service.parse_cv(cleaned_text, pages=pages)
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "CV parser failed to structure the CV",
                "error": str(exc),
            },
        ) from exc

    # --- BERT: skills only ---------------------------------------------
    # The model tags cities, companies and prose as SKILL, so keep only
    # skills that map to the canonical taxonomy.
    # ponytail: skills missing from the taxonomy are dropped. Extend
    # _CANONICAL_SKILL_ALIASES when matching needs them.
    classified_tokens: list[dict] = []
    try:
        bert_cv, classified_tokens = get_bert_classifier().extract_cv_structure(cleaned_text)
        parsed_cv.candidate_profile.skills = [
            skill for skill in bert_cv.candidate_profile.skills if skill in _CANONICAL_SKILLS
        ]
    except Exception:
        logger.exception("BERT skill extraction failed; keeping heuristic skills")

    return parsed_cv, classified_tokens


def _save_compatibility_scores(
    db: Session,
    profile_id: int,
    scores: list[dict],
) -> None:
    """Replace existing compatibility scores for a profile with new ones."""
    db.query(CompatibilityScore).filter(
        CompatibilityScore.profile_id == profile_id
    ).delete()
    db.flush()
    for item in scores:
        db.add(CompatibilityScore(
            profile_id=profile_id,
            job_id=item.get("job_id"),
            score=item.get("compatibility_score"),
        ))
    db.commit()


def _date_to_string(value: Any) -> str | None:
    return value.isoformat() if value else None


def _serialize_profile_for_review(profile: Profile) -> dict[str, Any]:
    cv = profile.cv

    return {
        "message": "CV profile loaded",
        "cv_id": profile.cv_id,
        "profile_id": profile.id,
        "cv_file_name": cv.filename if cv else None,
        "ai_result": {
            "candidate_profile": {
                "given_name": profile.given_name,
                "middle_name": profile.middle_name,
                "family_name": profile.family_name,
                "current_title": profile.current_title,
                "phone": profile.phone,
                "location": profile.location,
                "email": profile.email,
                "bio": profile.bio,
                "skills": _skills_as_list(profile.skills),
            },
            "work_experience": [
                {
                    "job_title": item.job_title,
                    "company_name": item.company_name,
                    "start_date": _date_to_string(item.start_date),
                    "end_date": _date_to_string(item.end_date),
                }
                for item in profile.work_experiences
            ],
            "education": [
                {
                    "institution": item.institution,
                    "degree": item.degree,
                    "field_of_study": item.field_of_study,
                    "start_date": _date_to_string(item.start_date),
                    "end_date": _date_to_string(item.end_date),
                }
                for item in profile.educations
            ],
            "projects": [
                {
                    "project_name": item.project_name,
                    "description": item.description,
                }
                for item in profile.projects
            ],
            "languages": [
                {
                    "language_name": item.language_name,
                    "proficiency_level": item.proficiency_level,
                }
                for item in profile.languages
            ],
            "certifications": [
                {
                    "certification_name": item.certification_name,
                    "issue_date": _date_to_string(item.issue_date),
                }
                for item in profile.certifications
            ],
        },
    }


@router.post("/cv/upload")
async def upload_cv_with_form_data(
    givenName: str = Form(...),
    middleName: str | None = Form(None),
    familyName: str = Form(...),
    email: str = Form(...),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    parsed_cv, classified_tokens = await _parse_uploaded_cv(cv)

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
    scores = job_service.calculate_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
        cv_skills=ai_result_dict.get("candidate_profile", {}).get("skills"),
    )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=normalized_filename,
            structured_data=ai_result_dict,
            compatibility_scores=scores,
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
        "delete_token": auth_service.create_cv_delete_token(profile.cv_id),
        "profile_id": profile.id,
        "compatibility_scores": scores,
        "ai_result": ai_result_dict,
        "classified_tokens": classified_tokens,
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

    # Recalculate compatibility scores with the confirmed (possibly edited) skills.
    scores = job_service.calculate_compatibility_scores(
        db,
        structured_data.get("skills_embedding"),
        cv_skills=structured_data.get("candidate_profile", {}).get("skills"),
    )

    try:
        _save_compatibility_scores(db, profile_id, scores)
    except Exception:
        pass  # scoring is best-effort; don't fail the save

    response_data = dict(structured_data)
    response_data.pop("skills_embedding", None)

    return {
        "message": "CV data updated",
        "cv_id": profile.cv_id,
        "profile_id": profile.id,
        "ai_result": response_data,
        "compatibility_scores": scores,
    }


@router.get("/cv/{profile_id}/extracted-data")
def get_extracted_cv_data(
    profile_id: int,
    db: Session = Depends(get_db),
):
    profile = (
        db.query(Profile)
        .options(
            joinedload(Profile.cv),
            joinedload(Profile.work_experiences),
            joinedload(Profile.educations),
            joinedload(Profile.projects),
            joinedload(Profile.languages),
            joinedload(Profile.certifications),
        )
        .filter(Profile.id == profile_id)
        .first()
    )

    if profile is None:
        raise HTTPException(status_code=404, detail="CV profile not found")

    return _serialize_profile_for_review(profile)


@router.delete("/cv/{cv_id}")
def delete_cv(
    cv_id: int,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_cv_delete_token: str | None = Header(None),
):
    # Uploader (incl. guests) proves ownership with the delete token returned on upload.
    # Otherwise: admins can delete any CV, users only the one matching their login email.
    if not auth_service.verify_cv_delete_token(cv_id, x_cv_delete_token):
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Authentication required")
        user = auth_service.verify_access_token(credentials.credentials)
        if user.get("role") != "admin":
            profile = db.query(Profile).filter(Profile.cv_id == cv_id).first()
            owner_email = (profile.email or "").strip().lower() if profile else ""
            if not owner_email or owner_email != str(user.get("sub", "")).strip().lower():
                raise HTTPException(status_code=403, detail="You can only delete your own CV")

    service.delete_CV_by_id(db, cv_id)

    return {"message": "CV deleted successfully", "cv_id": cv_id}


@router.post("/parse-cv")
async def parse_cv(
    cv: UploadFile = File(...),
    given_name: str | None = Form(None),
    middle_name: str | None = Form(None),
    family_name: str | None = Form(None),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
):
    parsed_cv, classified_tokens = await _parse_uploaded_cv(cv)

    generated_cv_name = build_cv_filename(
        given_name,
        middle_name,
        family_name,
    )

    ai_result_dict = _prepare_ai_result_with_skills_embedding(
        parsed_cv,
        given_name=given_name,
        middle_name=middle_name,
        family_name=family_name,
        email=email,
    )
    scores = job_service.calculate_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
        cv_skills=ai_result_dict.get("candidate_profile", {}).get("skills"),
    )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=generated_cv_name,
            structured_data=ai_result_dict,
            compatibility_scores=scores,
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
        "delete_token": auth_service.create_cv_delete_token(profile.cv_id),
        "profile_id": profile.id,
        "compatibility_scores": scores,
        "cv_file_name": generated_cv_name,
        "ai_result": ai_result_dict,
        "classified_tokens": classified_tokens,
    }


@router.get("/profiles/{profile_id}/all")
def calculate_all_compatibility_scores_for_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    return job_service.calculate_and_save_scores_for_profile(db, profile_id)

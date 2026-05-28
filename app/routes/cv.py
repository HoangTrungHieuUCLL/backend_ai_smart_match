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
@router.get("/cv/test")
async def test():
    return {
          "candidate_profile": {
            "id": 1,
            "given_name": "Eren",
            "family_name": "Derinbay",
            "current_title": "Applied Computer Science student",
            "phone": "+32 0498 51 50 67",
            "email": "eren.derinbay@gmail.com",
            "bio": "passionate problem solver. Strong at debugging and learning new technologies. Experienced working both independently and in Agile teams. Interested in programming from a young age and passionate about software development, UI/UX, and building tools that solve real problems.",
            "skills": "TypeScript, JavaScript, HTML/CSS, Java, Python, C#, Ruby, React, Next.js, Node.js, Prisma ORM, .NET (MAUI), SQL, PostgreSQL, MySQL, MongoDB, Azure, AWS, GitHub, GitHub Actions, Linux CLI, Agile, Scrum, UI/UX",
            "work_experiences": [
              {
                "id": 1,
                "profile_id": 1,
                "job_title": "Educational Assistant",
                "company_name": "CodeFever",
                "start_date": "March 2024",
                "end_date": "June 2025"
              }
            ],
            "educations": [
              {
                "id": 1,
                "profile_id": 1,
                "institution": "University Colleges Leuven-Limburg (UCLL)",
                "degree": "Bachelor of Applied Computer Science",
                "field_of_study": "Computer Science",
                "start_date": "September 2023",
                "end_date": "June 2026"
              },
              {
                "id": 2,
                "profile_id": 1,
                "institution": "Atlantic Technological University (ATU)",
                "start_date": "September 2025",
                "end_date": "January 2026"
              }
            ],
            "projects": [
              {
                "id": 1,
                "profile_id": 1,
                "project_name": "SteamList",
                "description": "Personal project A social cataloging platform for Steam libraries, developed solo for over 8+ months..."
              }
            ],
            "languages": [
              {
                "id": 1,
                "profile_id": 1,
                "language_name": "English",
                "proficiency_level": "C2"
              },
              {
                "id": 2,
                "profile_id": 1,
                "language_name": "Dutch",
                "proficiency_level": "full professional"
              },
              {
                "id": 3,
                "profile_id": 1,
                "language_name": "Turkish",
                "proficiency_level": "native"
              }
            ],
            "certifications": [],
            "compatibility_scores": []
      }
    }

@router.post("/parse-cv")
async def parse_cv(
    cv: UploadFile = File(...),
    given_name: str = Form(None),
    middle_name: str = Form(None),
    family_name: str = Form(None),
    email: str = Form(None),
    db: Session = Depends(get_db)
):
    parsed_cv = await _parse_uploaded_cv(cv)
    print("=======================")
    print(parsed_cv)
    print("=======================")
    ai_result_dict = _prepare_ai_result_with_skills_embedding(parsed_cv)

    top_10_scores = job_service.calculate_top_compatibility_scores(
        db,
        ai_result_dict.get("skills_embedding"),
    )

    # dict for DB, json string for response
    ai_result_dict = parsed_cv.model_dump()
    ai_result_dict.setdefault("candidate_profile", {})

    # inject frontend fields
    if given_name:
        ai_result_dict["candidate_profile"]["given_name"] = given_name
    if family_name:
        ai_result_dict["candidate_profile"]["family_name"] = family_name
    if middle_name:
        ai_result_dict["candidate_profile"]["middle_name"] = middle_name
    if email:
        ai_result_dict["candidate_profile"]["email"] = email

    ai_result_json = parsed_cv.model_dump_json()
    skills_embedding = embed_skills(ai_result_dict["candidate_profile"]["skills"])
    ai_result_dict["skills_embedding"] = skills_embedding
    print("FINAL EMAIL IN AI RESULT:", ai_result_dict["candidate_profile"].get("email"))
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
        "ai_result": ai_result_dict,
    }

@router.get("/profiles/{profile_id}/top10")
def get_top_10_compatibility_scores(
    profile_id: int,
    db: Session = Depends(get_db),
):
    return job_service.get_top_compatibility_scores_for_profile(
        db,
        profile_id,
        limit=10,
    )
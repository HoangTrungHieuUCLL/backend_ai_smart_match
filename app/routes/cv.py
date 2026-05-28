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

@router.post("/cv/upload")
async def upload_cv(
        db: Session = Depends(get_db)
):
    scores = job_service.assign_placeholder_compatability_scores(db)

    return scores


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
    skills_embedding = embed_skills(ai_result_dict["candidate_profile"]["skills"])
    ai_result_dict["skills_embedding"] = skills_embedding
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
        "ai_result": ai_result_dict,
    }
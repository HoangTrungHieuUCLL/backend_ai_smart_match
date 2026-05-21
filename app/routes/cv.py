from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService
import httpx

from app.models.cv import CV
from app.service.job import JobService

router = APIRouter()
service = CVService()
job_service = JobService()

AI_URL = "http://ai:8001/parse-cv"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/parse-cv")
async def upload_cv(
    # familyName: str = Form(...),
    # middleName: str = Form(None),
    # givenName: str = Form(...),
    # email: str = Form(...),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # # basic metadata log
    # print("CV received")
    # print("Name:", givenName, middleName, familyName)
    # print("Email:", email)
    # print("Filename:", cv.filename)
    
    file_bytes = await cv.read()
    # # read a small portion of the file
    # content = cv.file.read().decode("utf-8", errors="ignore")
    # preview_lines = content.splitlines()[:5]

    # print("First lines of CV:")
    # for line in preview_lines:
    #     print(line)

    # return {"message": "CV received"}
# send to AI service
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                AI_URL,
                files={"file": (cv.filename, file_bytes, cv.content_type)},
            )

    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="AI service timed out while waiting for Gemini. Try again or increase timeout."
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach AI service: {exc}"
        )

    # Important: check status code before reading response.json()
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI service failed before returning structured CV JSON",
                "ai_status_code": response.status_code,
                "ai_response": response.text,
            },
        )

    try:
        ai_result = response.json()

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AI service returned a non-JSON response",
                "ai_response": response.text,
            },
        )

    try:
        profile = service.save_ai_cv_result(
            db,
            filename=cv.filename or "uploaded_cv.pdf",
            structured_data=ai_result,
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
        "ai_result": ai_result,
    }
    # scores = job_service.assign_placeholder_compatability_scores(db)

    # return scores


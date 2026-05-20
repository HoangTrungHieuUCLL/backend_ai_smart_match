from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.cv import CVService

router = APIRouter()
service = CVService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cv/upload")
def upload_cv(
    familyName: str = Form(...),
    middleName: str = Form(None),
    givenName: str = Form(...),
    email: str = Form(...),
    cv: UploadFile = File(...),
):
    # basic metadata log
    print("CV received")
    print("Name:", givenName, middleName, familyName)
    print("Email:", email)
    print("Filename:", cv.filename)

    # read a small portion of the file
    content = cv.file.read().decode("utf-8", errors="ignore")
    preview_lines = content.splitlines()[:5]

    print("First lines of CV:")
    for line in preview_lines:
        print(line)

    return {"message": "CV received"}
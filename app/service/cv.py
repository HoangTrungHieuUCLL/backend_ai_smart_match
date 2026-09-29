from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.repository.cv import CVRepository

class CVService:
    def __init__(self):
        self.repo = CVRepository()

    def delete_CV_by_id(self, db: Session, CV_id: int):
        cv = self.repo.delete_by_id(db, CV_id)

        if cv is None:
            raise HTTPException(status_code=404, detail="CV not found")

        return cv

    def save_ai_cv_result(
        self,
        db: Session,
        *,
        filename: str,
        structured_data: dict,
        compatibility_scores: list[dict] | None = None,
    ):
        return self.repo.save_ai_result(
            db,
            filename=filename,
            structured_data=structured_data,
            compatibility_scores=compatibility_scores,
        )

    def update_ai_cv_result(
        self,
        db: Session,
        *,
        profile_id: int,
        structured_data: dict,
    ):
        return self.repo.update_ai_result(
            db,
            profile_id=profile_id,
            structured_data=structured_data,
        )

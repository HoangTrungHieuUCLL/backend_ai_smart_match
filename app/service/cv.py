from sqlalchemy.orm import Session
from app.repository.cv import CVRepository

class CVService:
    def __init__(self):
        self.repo = CVRepository()

    def get_all_CVs(self, db: Session):
        return self.repo.get_all(db)

    def get_CV_by_id(self, db: Session, CV_id: int):
        return self.repo.get_by_id(db, CV_id)

    def save_ai_cv_result(
        self,
        db: Session,
        *,
        filename: str,
        structured_data: dict[str, any],
    ): 
        return self.repo.save_ai_result(
            db,
            filename=filename,
            sturctured_data= structured_data,
        )
from sqlalchemy.orm import Session

from app.models import CV
from app.models.job import Job

class CVRepository:

    def get_all(self, db: Session):
        return db.query(CV).all()

    def get_by_id(self, db: Session, cv_id: int):
        return db.query(CV).filter(CV.id == cv_id).first()

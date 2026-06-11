from sqlalchemy.orm import Session
from app.models import Profile

class ProfileRepository:

    def get_by_id(self, db: Session, profile_id: int):
        return db.query(Profile).filter(Profile.id == profile_id).first()

    def get_by_email(self, db: Session, email: str):
        return db.query(Profile).filter(Profile.email == email).first()
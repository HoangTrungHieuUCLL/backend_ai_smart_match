from sqlalchemy.orm import Session
from app.repository.profile import ProfileRepository

class ProfileService:
    def __init__(self):
        self.repo = ProfileRepository()

    def get_by_id(self, db: Session, profile_id: int):
        return self.repo.get_by_id(db, profile_id)

    def get_by_email(self, db: Session, email: str):
        return self.repo.get_by_email(db, email)
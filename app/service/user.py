from sqlalchemy.orm import Session
from app.repository.user import UserRepository
from app.schemas.user import UserCreate

class UserService:
    def __init__(self):
        self.repo = UserRepository()

    def get_all_users(self, db: Session):
        return self.repo.get_all(db)

    def get_user_by_id(self, db: Session, user_id: int):
        return self.repo.get_by_id(db, user_id)

    def create_user(self, db: Session, user: UserCreate):
        return self.repo.create(db, user)

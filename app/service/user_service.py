import csv
import os
import hashlib
from typing import Optional, Dict


USER_FILE = "app/schemas/users.csv"


class UserService:
    def __init__(self):
        os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)

        # create file if it doesn't exist
        if not os.path.exists(USER_FILE):
            with open(USER_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["email", "password_hash", "role"])

    # HASHING
    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, hashed: str) -> bool:
        return self.hash_password(password) == hashed
    # READ USERS

    def _read_users(self) -> list[dict]:
        with open(USER_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def find_by_email(self, email: str) -> Optional[Dict]:
        normalized_email = email.strip().lower()
        users = self._read_users()
        for user in users:
            if user["email"].strip().lower() == normalized_email:
                return user
        return None

    def email_exists(self, email: str) -> bool:
        return self.find_by_email(email) is not None

    # CREATE USER

    def create_user(self, email: str, password: str, role: str = "user") -> dict:
        if self.email_exists(email):
            raise ValueError("EMAIL_EXISTS")

        hashed = self.hash_password(password)

        with open(USER_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([email, hashed, role])

        return {
            "email": email,
            "role": role,
        }

    def update_password(self, email: str, new_password: str) -> None:
        normalized_email = email.strip().lower()
        users = self._read_users()
        updated = False

        for user in users:
            if user["email"].strip().lower() == normalized_email:
                user["password_hash"] = self.hash_password(new_password)
                updated = True
                break

        if not updated:
            raise ValueError("USER_NOT_FOUND")

        with open(USER_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "password_hash", "role"])
            writer.writeheader()
            writer.writerows(users)


user_service = UserService()

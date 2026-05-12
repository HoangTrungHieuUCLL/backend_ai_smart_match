import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartmatch")

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
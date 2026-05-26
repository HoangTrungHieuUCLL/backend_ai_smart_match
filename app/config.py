import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join("app", ".env"))

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartmatch")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
GEMINI_API_KEY = settings.GEMINI_API_KEY

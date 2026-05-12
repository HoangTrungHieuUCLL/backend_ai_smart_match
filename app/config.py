import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/ai_smart_match")

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
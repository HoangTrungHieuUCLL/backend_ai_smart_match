import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join("app", ".env"))

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartmatch")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    SEED_ON_STARTUP = os.getenv("SEED_ON_STARTUP", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-auth-secret")
    AUTH_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_TOKEN_EXPIRE_SECONDS", "3600"))

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
GEMINI_API_KEY = settings.GEMINI_API_KEY
CORS_ORIGINS = settings.CORS_ORIGINS
SEED_ON_STARTUP = settings.SEED_ON_STARTUP
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
AUTH_SECRET_KEY = settings.AUTH_SECRET_KEY
AUTH_TOKEN_EXPIRE_SECONDS = settings.AUTH_TOKEN_EXPIRE_SECONDS

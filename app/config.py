import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join("app", ".env"))


def _normalize_database_url(url: str) -> str:
    # Some providers (Railway, Heroku) hand out "postgres://", which
    # SQLAlchemy's create_engine no longer recognizes as a dialect.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Settings:
    DATABASE_URL = _normalize_database_url(
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartmatch")
    )
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-auth-secret")
    AUTH_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_TOKEN_EXPIRE_SECONDS", "3600"))
    LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI = os.getenv(
        "LINKEDIN_REDIRECT_URI",
        "http://localhost:8000/auth/linkedin/cv-callback",
    )
    LINKEDIN_LOGIN_REDIRECT_URI = os.getenv(
        "LINKEDIN_LOGIN_REDIRECT_URI",
        "http://localhost:8000/auth/linkedin/login-callback",
    )
    LINKEDIN_REGISTER_REDIRECT_URI = os.getenv(
        "LINKEDIN_REGISTER_REDIRECT_URI",
        "http://localhost:8000/auth/linkedin/register-callback",
    )
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
    SEED_ON_STARTUP = os.getenv("SEED_ON_STARTUP", "true").lower() == "true"
    COMPATIBILITY_CALIBRATION_PATH = os.getenv("COMPATIBILITY_CALIBRATION_PATH")
    COMPATIBILITY_DBSCAN_EPS = float(os.getenv("COMPATIBILITY_DBSCAN_EPS", "0.24"))
    COMPATIBILITY_DBSCAN_MIN_SAMPLES = int(os.getenv("COMPATIBILITY_DBSCAN_MIN_SAMPLES", "1"))
    COMPATIBILITY_COVERAGE_WEIGHT = float(os.getenv("COMPATIBILITY_COVERAGE_WEIGHT", "0.58"))
    COMPATIBILITY_PRECISION_WEIGHT = float(os.getenv("COMPATIBILITY_PRECISION_WEIGHT", "0.27"))
    COMPATIBILITY_TAXONOMY_WEIGHT = float(os.getenv("COMPATIBILITY_TAXONOMY_WEIGHT", "0.15"))

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
AUTH_SECRET_KEY = settings.AUTH_SECRET_KEY
AUTH_TOKEN_EXPIRE_SECONDS = settings.AUTH_TOKEN_EXPIRE_SECONDS
LINKEDIN_CLIENT_ID = settings.LINKEDIN_CLIENT_ID
LINKEDIN_CLIENT_SECRET = settings.LINKEDIN_CLIENT_SECRET
LINKEDIN_REDIRECT_URI = settings.LINKEDIN_REDIRECT_URI
LINKEDIN_LOGIN_REDIRECT_URI = settings.LINKEDIN_LOGIN_REDIRECT_URI
LINKEDIN_REGISTER_REDIRECT_URI = settings.LINKEDIN_REGISTER_REDIRECT_URI
FRONTEND_URL = settings.FRONTEND_URL
CORS_ORIGINS = settings.CORS_ORIGINS
SEED_ON_STARTUP = settings.SEED_ON_STARTUP

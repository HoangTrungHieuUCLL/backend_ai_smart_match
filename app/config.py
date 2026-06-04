import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join("app", ".env"))

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/smartmatch")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-auth-secret")
    AUTH_TOKEN_EXPIRE_SECONDS = int(os.getenv("AUTH_TOKEN_EXPIRE_SECONDS", "3600"))
    COMPATIBILITY_CALIBRATION_PATH = os.getenv("COMPATIBILITY_CALIBRATION_PATH")
    COMPATIBILITY_DBSCAN_EPS = float(os.getenv("COMPATIBILITY_DBSCAN_EPS", "0.24"))
    COMPATIBILITY_DBSCAN_MIN_SAMPLES = int(os.getenv("COMPATIBILITY_DBSCAN_MIN_SAMPLES", "1"))
    COMPATIBILITY_COVERAGE_WEIGHT = float(os.getenv("COMPATIBILITY_COVERAGE_WEIGHT", "0.58"))
    COMPATIBILITY_PRECISION_WEIGHT = float(os.getenv("COMPATIBILITY_PRECISION_WEIGHT", "0.27"))
    COMPATIBILITY_TAXONOMY_WEIGHT = float(os.getenv("COMPATIBILITY_TAXONOMY_WEIGHT", "0.15"))

settings = Settings()

# Allow direct import too
DATABASE_URL = settings.DATABASE_URL
GEMINI_API_KEY = settings.GEMINI_API_KEY
ADMIN_USERNAME = settings.ADMIN_USERNAME
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
AUTH_SECRET_KEY = settings.AUTH_SECRET_KEY
AUTH_TOKEN_EXPIRE_SECONDS = settings.AUTH_TOKEN_EXPIRE_SECONDS

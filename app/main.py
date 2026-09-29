from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
import app.models
from app.database import Base, engine, ensure_vector_extension
from app.routes.job import router as job_router
from app.routes.cv import router as cv_router
from app.routes.auth import router as auth_router
from app.routes.executive import router as executive_router
from app.routes.savedJobs import router as saved_jobs_router
from app.seed import seed_jobs
from app.config import CORS_ORIGINS
from app.service.bert_cv_classifier import get_bert_classifier
from app.service.cv_embedding_service import get_model as get_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    # Startup
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    seed_jobs()

    # Preload CV-parsing models so the first upload isn't the one paying for it.
    try:
        get_bert_classifier()._load()
    except Exception:
        pass  # falls back to heuristic parser at request time if unavailable
    try:
        get_embedding_model()
    except Exception:
        pass

    yield

    # Shutdown (optional)
    # e.g. close DB connections if needed


app = FastAPI(lifespan=lifespan)

default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]
env_origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=env_origins or default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API running"}


app.include_router(job_router)
app.include_router(cv_router)
app.include_router(auth_router)
app.include_router(executive_router)
app.include_router(saved_jobs_router)

from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
import app.models
from app.database import Base, engine, ensure_vector_extension
from app.routes.job import router as job_router
from app.routes.cv import router as cv_router
from app.routes.auth import router as auth_router
from app.seed import seed_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    # Startup
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    seed_jobs()

    yield

    # Shutdown (optional)
    # e.g. close DB connections if needed


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
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

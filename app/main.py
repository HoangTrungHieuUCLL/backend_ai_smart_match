from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
import app.models
from app.database import Base, engine, ensure_vector_extension
from app.routes.job import router as job_router
from app.routes.cv import router as cv_router
from app.seed import seed_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)

    async def seed_jobs_background():
        try:
            await asyncio.to_thread(seed_jobs)
        except Exception as exc:
            print(f"Background job seeding failed: {exc}")

    asyncio.create_task(seed_jobs_background())

    yield

    # Shutdown (optional)
    # e.g. close DB connections if needed


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API running"}


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


app.include_router(job_router)
app.include_router(cv_router)

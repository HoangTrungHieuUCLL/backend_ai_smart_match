from fastapi import FastAPI
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware

import app.models
from app.database import Base, engine
from app.routes.user import router as user_router
from app.routes.job import router as job_router
from app.routes.cv import router as cv_router
from app.seed import seed_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API running"}


app.include_router(user_router)
app.include_router(job_router)
app.include_router(cv_router)
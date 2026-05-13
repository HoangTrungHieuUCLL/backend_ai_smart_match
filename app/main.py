from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import Base, engine
from app.routes.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)

    yield

    # Shutdown (optional)
    # e.g. close DB connections if needed


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "API running"}


app.include_router(user_router)
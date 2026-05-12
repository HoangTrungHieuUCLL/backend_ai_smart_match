from fastapi import FastAPI

from app.database import Base, engine
from app.routes.user import router as user_router

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "API running"}

app.include_router(user_router)

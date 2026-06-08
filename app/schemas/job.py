from pydantic import BaseModel, validator
from typing import Optional

class JobCreate(BaseModel):
    company_name: str
    position: str
    date: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    overview: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    requirements_simplified: Optional[str] = None
    offers: Optional[str] = None
    salary: Optional[str] = None
    notes: Optional[str] = None

class JobUpdate(BaseModel):
    company_name: str
    position: str
    date: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    overview: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    requirements_simplified: Optional[str] = None
    offers: Optional[str] = None
    salary: Optional[str] = None
    notes: Optional[str] = None

class Job(BaseModel):
    id: int
    company_name: str
    position: str
    date: str
    location: str
    type: str
    overview: str
    responsibilities: str
    requirements: str
    requirements_simplified: Optional[str] = None
    requirements_embedding: Optional[list[float]] = None
    offers: str
    salary: str
    notes: str

    @validator("requirements_embedding", pre=True)
    def serialize_embedding(cls, value):
        if hasattr(value, "tolist"):
            return value.tolist()
        return value

    class Config:
        from_attributes = True

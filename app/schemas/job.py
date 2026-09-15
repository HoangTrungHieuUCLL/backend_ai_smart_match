from pydantic import BaseModel, validator
from typing import Optional

class _JobTaxonomyFields(BaseModel):
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    category_l3: Optional[str] = None
    experience_level: Optional[str] = None
    seniority: Optional[str] = None
    employment_type: Optional[str] = None
    work_arrangement: Optional[str] = None
    saturday_work: Optional[str] = None
    work_schedule: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_unit: Optional[str] = None
    salary_negotiable: Optional[bool] = False
    company_industry: Optional[str] = None
    is_featured_employer: Optional[bool] = False

class JobCreate(_JobTaxonomyFields):
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

class JobUpdate(_JobTaxonomyFields):
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

class Job(_JobTaxonomyFields):
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

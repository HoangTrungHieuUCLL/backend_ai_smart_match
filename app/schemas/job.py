from pydantic import BaseModel

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
    offers: str
    salary: str
    notes: str

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String)
    position = Column(String)
    date = Column(String)
    location = Column(String)
    type = Column(String)
    overview = Column(Text)
    responsibilities = Column(Text)
    requirements = Column(Text)
    requirements_simplified = Column(Text)
    requirements_embedding = Column(Vector(384))
    offers = Column(Text)
    salary = Column(String)
    notes = Column(Text)

    # Filter taxonomy (client feedback v2). Slugs from app/constants/job_taxonomy.py.
    category_l1 = Column(String)
    category_l2 = Column(String)
    category_l3 = Column(String)
    experience_level = Column(String)
    seniority = Column(String)
    employment_type = Column(String)
    work_arrangement = Column(String)
    saturday_work = Column(String)
    work_schedule = Column(String)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_unit = Column(String)
    salary_negotiable = Column(Boolean, default=False)
    company_industry = Column(String)
    is_featured_employer = Column(Boolean, default=False)

    compatibility_scores = relationship(
        "CompatibilityScore",
        back_populates="job",
        cascade="all, delete-orphan"
    )
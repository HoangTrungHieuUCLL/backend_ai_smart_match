from sqlalchemy import Column, Integer, String, Text
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

    compatibility_scores = relationship(
        "CompatibilityScore",
        back_populates="job",
        cascade="all, delete-orphan"
    )
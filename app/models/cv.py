from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class CV(Base):
    __tablename__ = "cv"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    original_filename = Column(String, nullable=False)
    file_url = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    candidate_profile = relationship("CandidateProfile", back_populates="cv", uselist=False)
    matches = relationship("CVJobMatch", back_populates="cv")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cv.id"), nullable=False, unique=True)

    given_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    family_name = Column(String, nullable=True)
    current_title = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    email = Column(String, nullable=True)
    summary = Column(Text, nullable=True)

    cv = relationship("CV", back_populates="candidate_profile")
    skills = relationship("Skill", back_populates="profile")
    work_experiences = relationship("WorkExperience", back_populates="profile")
    educations = relationship("Education", back_populates="profile")
    projects = relationship("Project", back_populates="profile")
    languages = relationship("CandidateLanguage", back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)

    skill_name = Column(String, nullable=False)
    skill_type = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)

    profile = relationship("CandidateProfile", back_populates="skills")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)

    job_title = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    profile = relationship("CandidateProfile", back_populates="work_experiences")


class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)

    institution_name = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    profile = relationship("CandidateProfile", back_populates="educations")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)

    project_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    project_url = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    profile = relationship("CandidateProfile", back_populates="projects")


class CandidateLanguage(Base):
    __tablename__ = "candidate_languages"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)

    language_name = Column(String, nullable=False)
    proficiency_level = Column(String, nullable=True)

    profile = relationship("CandidateProfile", back_populates="languages")


class CVJobMatch(Base):
    __tablename__ = "cv_job_matches"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, ForeignKey("cv.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    compatibility_score = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cv = relationship("CV", back_populates="matches")
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

# For Gemini
class CV(Base):
    __tablename__ = "cv"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    candidate_profile = relationship(
        "Profile",
        back_populates="cv",
        uselist=False,
    )


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(
        Integer, 
        ForeignKey("cv.id", ondelete="SET NULL"), 
        nullable=True, 
        unique=True
        )

    given_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    family_name = Column(String, nullable=False)
    current_title = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    email = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

    cv = relationship("CV", back_populates="candidate_profile")

    work_experiences = relationship(
        "Experience",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    educations = relationship(
        "Education",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    projects = relationship(
        "Project",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    languages = relationship(
        "Language",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    certifications = relationship(
        "Certification",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

class Experience(Base):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    job_title = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    profile = relationship("Profile", back_populates="work_experiences")


class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    institution = Column(String, nullable=True)
    degree = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    profile = relationship("Profile", back_populates="educations")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    project_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    profile = relationship("Profile", back_populates="projects")


class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    language_name = Column(String, nullable=True)
    proficiency_level = Column(String, nullable=True)

    profile = relationship("Profile", back_populates="languages")

class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)

    certification_name = Column(String, nullable=True)
    issue_date = Column(Date, nullable=True)

    profile = relationship("Profile", back_populates="certifications")
from pydantic import BaseModel
from typing import List, Optional


# class Skill(BaseModel):
#     skill_name: str

# For backend
class WorkExperience(BaseModel):
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Project(BaseModel):
    project_name: Optional[str] = None
    description: Optional[str] = None


class CandidateLanguage(BaseModel):
    language_name: Optional[str] = None
    proficiency_level: Optional[str] = None


class CandidateProfile(BaseModel):
    # given_name: Optional[str] = None
    # middle_name: Optional[str] = None
    # family_name: Optional[str] = None
    current_title: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    # email: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = []

class Certification(BaseModel):
    certification_name: Optional[str] = None
    issue_date: Optional[str] = None

class CVParsed(BaseModel):
    candidate_profile: Optional[CandidateProfile] = None
    work_experience: List[WorkExperience] = []
    education: List[Education] = []
    projects: List[Project] = []
    languages: List[CandidateLanguage] = []
    certifications: List[Certification] = []
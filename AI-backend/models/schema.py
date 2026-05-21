#not used currently

from pydantic import BaseModel
from typing import List, Optional

class Skill(BaseModel):
    skillName: str
    skillType: Optional[str] = None
    # confidenceScore: float = 0.0


class Experience(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None


class Education(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None



class Project(BaseModel):
    name: Optional[str] = None


class Language(BaseModel):
    languageName: str
    proficiencyLevel: Optional[str] = None

class Certification(BaseModel):
    name: str
class CVParsed(BaseModel):
    # email: Optional[str] = None
    skills: List[Skill] = []
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    languages: List[Language] = []
    certifications: List[Certification] = []
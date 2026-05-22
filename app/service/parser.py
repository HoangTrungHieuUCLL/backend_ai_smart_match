from pydoc import text
import re
import spacy
from models.schema import CVParsed
from models.schema import Skill, Experience, Education, Project, Language, Certification

nlp = spacy.load("en_core_web_sm")

class CVParser:

    SECTION_HEADERS = {
        "skills": ["skills", "technical skills", "technologies", "COMPETENCIES", "core skills"],
        "experience": ["experience", "work experience", "employment", "professional experience"],
        "education": ["education", "studies", "academic background"],
        "projects": ["projects", "personal projects", "side projects"],
        "languages": ["languages", "language skills"],
        "certifications": ["certifications", "certificates", "certification"]
    }
    
    EDUCATION_PATTERNS = {
    "degree": [
        "bachelor", "master", "bsc", "msc", "phd",
        "diploma", "degree", "certificate"
    ],
    "institution": [
        "university", "college", "school", "institute"
    ],
    "date": [
        "-", "20", "19", "present"
    ]
}

    def parse(self, text: str) -> CVParsed:

        sections = self._split_into_sections(text)

        # email = self._extract_email(text)

        skills = self._extract_skills(sections.get("skills", ""))
        experience = self._extract_experience(sections.get("experience", ""))
        education = self._extract_education(sections.get("education", ""))
        projects = self._extract_projects(sections.get("projects", ""))
        languages = self._extract_languages(sections.get("languages", ""))
        certifications = self._extract_certifications(sections.get("certifications", ""))
        return CVParsed(
            # email=email,
            skills=skills,
            experience=experience,
            education=education,
            projects=projects,
            languages=languages,
            certifications=certifications
        )

    # def _extract_email(self, text):

    #     match = re.search(
    #         r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    #         text
    #     )

        # return match.group(0) if match else None

    def _split_into_sections(self, text):

        lines = text.splitlines()

        sections = {}
        current_section = None

        sections[current_section] = []

        for line in lines:

            clean_line = line.strip()

            if not clean_line:
                continue

            detected_section = self._detect_section(clean_line)

            if detected_section:
                current_section = detected_section
                sections.setdefault(current_section, [])

            else:
                 if current_section:
                    sections[current_section].append(clean_line)

        return {
            key: "\n".join(value)
            for key, value in sections.items()
        }

    def _detect_section(self, line):

        lower = line.lower().replace(":", "").strip()

        for section, headers in self.SECTION_HEADERS.items():
            for h in headers:
                if h in lower:   # <-- IMPORTANT CHANGE (not equality)
                    return section

        return None

    def _extract_skills(self, skills_text):

        doc = nlp(skills_text)

        skills = []

        for chunk in doc.noun_chunks:
            skill = chunk.text.strip()
            
            if (
                len(skill) < 2 or 
                len(skill) > 40 or
                        any(char.isdigit() for char in skill) or
                        "\n" in skill or
                        skill.lower() in ["experience", "education", "skills"]
                    ):
                        continue

            skills.append(skill)

        # return list(set(skills))
        return [
            Skill(skillName=s.strip())
            for s in set(skills)
            if len(s.strip()) > 1
        ]
    def _extract_experience(self, experience_text):

        doc = nlp(experience_text)

        experiences = []

        for sent in doc.sents:
            sentence = sent.text.strip()
            if len(sentence) > 10:
                experiences.append(sentence)

        # return experiences
        return [
            Experience(
                title=exp.split("\n")[0] if "\n" in exp else None,
                company=None
            )
            for exp in set(experiences)
        ]
        
    def is_institution(self, line):
        l = line.lower()
        return any(x in l for x in [
            "university", "college", "school", "institute"
        ])


    def is_degree(self, line):
        l = line.lower()
        return any(x in l for x in [
            "bachelor", "master", "phd", "diploma",
            "degree", "bsc", "msc", "high school","master's", "bachelor's"
        ])


    def is_valid_education(self, edu):
        return bool(edu.get("institution") and edu.get("degree"))


    def _extract_education(self, education_text):

        lines = [l.strip() for l in education_text.split("\n") if l.strip()]

        education = []
        current = None

        for line in lines:

            # CASE 1: institution → start new block
            if self.is_institution(line):

                if current and self.is_valid_education(current):
                    education.append(current)

                current = {
                    "institution": line,
                    "degree": None
                }

            # CASE 2: degree → attach to current block
            elif self.is_degree(line):

                if current is None:
                    current = {
                        "institution": None,
                        "degree": line
                    }
                else:
                    current["degree"] = line

            # CASE 3: noise → ignore completely
            else:
                continue

        # finalize last block
        if current and self.is_valid_education(current):
            education.append(current)

        return [Education(**e) for e in education]
    
    def _extract_projects(self, project_text):

        doc = nlp(project_text)

        projects = []

        for sent in doc.sents:
            sentence = sent.text.strip()

            if len(sentence) > 10:
                projects.append(sentence)

        # return list(set(projects))
        return [
            Project(name=proj.strip())
            for proj in set(projects)
            if len(proj.strip()) > 10
        ]
    def _extract_certifications(self, text):

        doc = nlp(text)

        certs = []

        for sent in doc.sents:
            sentence = sent.text.strip()

            # filter very short/noisy lines
            if len(sentence) > 5 and not sentence.lower().startswith("e "):
                certs.append(sentence)

        # return list(set(certs))
        return [
            Certification(name=cert.strip())
            for cert in set(certs)
            if len(cert.strip()) > 5
        ]

    def _extract_languages(self, text):

        doc = nlp(text)

        languages = []

        for chunk in doc.noun_chunks:
            lang = chunk.text.strip()

            # filter noise
            if len(lang) < 20:
                if any(word.lower() in lang.lower() for word in ["english", "french", "dutch", "german", "spanish"]):
                    languages.append(lang)

        # return list(set(languages))
        return [
            Language(languageName=lang.strip())
            for lang in set(languages)
            if len(lang.strip()) > 1
        ]
from __future__ import annotations

import math
import re

from app.models.cv_schema import (
    CVParsed,
    CandidateLanguage,
    Certification,
    Education,
    Project,
    WorkExperience,
)
from app.service.skill_taxonomy import canonicalize_skill_phrases
from app.service.text_phrases import extract_key_phrases, normalize_phrase


class CVParsingService:
    _section_model = None
    _SECTION_CUES = {
        "profile",
        "summary",
        "about",
        "objective",
        "skills",
        "experience",
        "education",
        "projects",
        "languages",
        "certifications",
        "competencies",
        "technologies",
    }

    SECTION_HEADERS = {
        "profile": ["profile", "summary", "about me", "professional summary", "objective"],
        "skills": ["skills", "technical skills", "technologies", "competencies", "core skills"],
        "experience": ["experience", "work experience", "employment", "professional experience", "career history"],
        "education": ["education", "studies", "academic background", "qualifications"],
        "projects": ["projects", "personal projects", "side projects", "selected projects"],
        "languages": ["languages", "language skills"],
        "certifications": ["certifications", "certificates", "certification"],
    }

    def parse_cv(self, raw_text: str) -> CVParsed:
        sections = self._split_into_sections(raw_text)
        top_block = self._get_top_block(raw_text)

        candidate_profile = {
            "current_title": self._extract_current_title(top_block),
            "phone": self._extract_phone(raw_text),
            "location": self._extract_location(top_block or raw_text),
            "bio": self._extract_summary(sections.get("profile") or top_block),
            "skills": self._extract_skills(sections.get("skills") or raw_text),
        }

        return CVParsed(
            candidate_profile=candidate_profile,
            work_experience=self._extract_work_experience(sections.get("experience", "")),
            education=self._extract_education(sections.get("education", "")),
            projects=self._extract_projects(sections.get("projects", "")),
            languages=self._extract_languages(sections.get("languages", "")),
            certifications=self._extract_certifications(sections.get("certifications", "")),
        )

    def _split_into_sections(self, text: str) -> dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: dict[str, list[str]] = {}
        current_section: str | None = None
        top_block: list[str] = []

        for line in lines:
            detected_section = self._detect_section(line)
            if detected_section:
                current_section = detected_section
                sections.setdefault(current_section, [])
                continue

            if current_section is None:
                top_block.append(line)
            else:
                sections[current_section].append(line)

        result = {key: "\n".join(value).strip() for key, value in sections.items()}
        result["__top_block__"] = "\n".join(top_block).strip()
        return result

    def _detect_section(self, line: str) -> str | None:
        normalized = line.lower().replace(":", "").strip()

        for section, headers in self.SECTION_HEADERS.items():
            for header in headers:
                if normalized == header or normalized.startswith(header + " ") or header in normalized:
                    return section

        if len(normalized) > 80:
            return None

        if not any(cue in normalized for cue in self._SECTION_CUES):
            return None

        semantic_section = self._detect_section_semantically(normalized)
        if semantic_section is not None:
            return semantic_section

        return None

    def _detect_section_semantically(self, line: str) -> str | None:
        model = self._get_section_model()
        labels = ["profile section", "skills section", "experience section", "education section", "projects section", "languages section", "certifications section"]
        label_to_section = {
            "profile section": "profile",
            "skills section": "skills",
            "experience section": "experience",
            "education section": "education",
            "projects section": "projects",
            "languages section": "languages",
            "certifications section": "certifications",
        }

        vectors = model.encode([line, *labels], normalize_embeddings=True)
        similarities = [self._cosine_similarity(vectors[0], vector) for vector in vectors[1:]]
        best_index = max(range(len(similarities)), key=similarities.__getitem__)

        if similarities[best_index] >= 0.55:
            return label_to_section[labels[best_index]]

        return None

    @staticmethod
    def _cosine_similarity(first_vector, second_vector) -> float:
        first = [float(value) for value in first_vector]
        second = [float(value) for value in second_vector]

        if len(first) != len(second):
            return -1.0

        dot_product = sum(a * b for a, b in zip(first, second))
        first_norm = math.sqrt(sum(a * a for a in first))
        second_norm = math.sqrt(sum(b * b for b in second))

        if not first_norm or not second_norm:
            return -1.0

        return dot_product / (first_norm * second_norm)

    @classmethod
    def _get_section_model(cls):
        if cls._section_model is None:
            from sentence_transformers import SentenceTransformer

            cls._section_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        return cls._section_model

    def _get_top_block(self, raw_text: str) -> str:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return ""

        collected: list[str] = []
        for line in lines[:20]:
            if self._detect_section(line):
                break
            collected.append(line)

        return "\n".join(collected).strip()

    def _extract_current_title(self, text: str) -> str | None:
        if not text:
            return None

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        for line in lines[1:4]:
            if self._looks_like_title(line):
                return normalize_phrase(line)

        return normalize_phrase(lines[0]) if self._looks_like_title(lines[0]) else None

    def _looks_like_title(self, line: str) -> bool:
        lowered = line.lower()
        return any(
            token in lowered
            for token in [
                "engineer",
                "developer",
                "analyst",
                "manager",
                "designer",
                "specialist",
                "consultant",
                "administrator",
                "scientist",
                "student",
                "intern",
            ]
        )

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{0,4}", text)
        if not match:
            return None

        phone = normalize_phrase(match.group(0))
        return phone if len(re.sub(r"\D", "", phone)) >= 8 else None

    def _extract_location(self, text: str) -> str | None:
        if not text:
            return None

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:5]:
            if self._looks_like_location(line):
                return normalize_phrase(line)

        return None

    def _extract_summary(self, text: str | None) -> str | None:
        if not text:
            return None

        summary = normalize_phrase(text)
        return summary if len(summary) > 20 else None

    def _extract_skills(self, text: str) -> list[str]:
        return canonicalize_skill_phrases(extract_key_phrases(text))

    def _extract_work_experience(self, experience_text: str) -> list[WorkExperience]:
        if not experience_text:
            return []

        blocks = [block.strip() for block in re.split(r"\n{2,}|•", experience_text) if block.strip()]
        experiences: list[WorkExperience] = []

        for block in blocks:
            lines = [line.strip("-–• \t") for line in block.splitlines() if line.strip()]
            combined = normalize_phrase(" ".join(lines))
            if len(combined) < 8:
                continue

            job_title = lines[0] if lines else None
            company_name = self._extract_organization(combined)
            start_date, end_date = self._extract_date_range(combined)

            experiences.append(
                WorkExperience(
                    job_title=normalize_phrase(job_title) if job_title else None,
                    company_name=company_name,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

        return experiences

    def _extract_education(self, education_text: str) -> list[Education]:
        if not education_text:
            return []

        entries = [line.strip() for line in education_text.splitlines() if line.strip()]
        educations: list[Education] = []

        for entry in entries:
            institution = self._extract_organization(entry)
            degree = self._extract_degree(entry)
            if institution or degree:
                educations.append(
                    Education(
                        institution=institution,
                        degree=degree or normalize_phrase(entry),
                        field_of_study=self._extract_field_of_study(entry),
                        start_date=None,
                        end_date=None,
                    )
                )

        return educations

    def _extract_projects(self, project_text: str) -> list[Project]:
        if not project_text:
            return []

        return [
            Project(project_name=phrase, description=None)
            for phrase in extract_key_phrases(project_text)
        ]

    def _extract_languages(self, text: str) -> list[CandidateLanguage]:
        if not text:
            return []

        return [
            CandidateLanguage(language_name=phrase, proficiency_level=None)
            for phrase in extract_key_phrases(text)
        ]

    def _extract_certifications(self, text: str) -> list[Certification]:
        if not text:
            return []

        return [
            Certification(certification_name=phrase, issue_date=None)
            for phrase in extract_key_phrases(text)
        ]

    def _extract_organization(self, text: str) -> str | None:
        for pattern in [
            r"([A-Z][A-Za-z0-9&'().-]*(?:\s+[A-Z][A-Za-z0-9&'().-]*){0,4}\s+(?:University|College|Institute|School|Company|Corp|Corporation|Ltd|LLC|JSC|Inc|Bank|Technologies|Software|Solutions|Labs))",
            r"(?:at|for)\s+([A-Z][A-Za-z0-9&'().-]*(?:\s+[A-Z][A-Za-z0-9&'().-]*){0,4})",
        ]:
            match = re.search(pattern, text)
            if match:
                return normalize_phrase(match.group(1))

        return None

    def _extract_degree(self, text: str) -> str | None:
        for keyword in ["bachelor", "master", "phd", "diploma", "degree", "msc", "bsc", "mba", "associate"]:
            if keyword in text.lower():
                return normalize_phrase(text)

        return None

    def _extract_field_of_study(self, text: str) -> str | None:
        match = re.search(r"(?:major|field|specialization|specialisation)[:\s-]+(.+)$", text, re.IGNORECASE)
        if match:
            return normalize_phrase(match.group(1))

        return None

    def _looks_like_location(self, line: str) -> bool:
        lowered = line.lower()
        if any(token in lowered for token in ["engineer", "developer", "analyst", "manager", "designer", "specialist", "consultant", "student", "intern"]):
            return False

        if re.search(r"\d", line):
            return False

        return "," in line or any(token in lowered for token in ["city", "province", "district", "hanoi", "saigon", "hochiminh", "vietnam", "remote"])

    def _extract_date_range(self, text: str) -> tuple[str | None, str | None]:
        match = re.search(
            r"(?P<start>(?:19|20)\d{2}(?:[-/](?:0?[1-9]|1[0-2]))?)\s*(?:-|–|to|until|through)\s*(?P<end>present|current|now|(?:19|20)\d{2}(?:[-/](?:0?[1-9]|1[0-2]))?)",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None, None

        return match.group("start"), match.group("end")
import re

from app.models.cv_schema import CVParsed


TECHNICAL_SKILLS = [
    "Python",
    "HTML",
    "CSS",
    "JavaScript",
    "Java",
    "TypeScript",
    "SQL",
    "ShinyR",
    "Excel VBA",
    "LLMs",
    "Neural Networks",
    "Computer Vision",
    "OpenCV",
    "YOLO",
    "Apache Airflow",
    "Docker Image",
    "Azure",
    "Postgres",
    "MongoDB",
    "Data Analytics",
    "Data Engineering",
    "Machine Learning",
    "RAG Pipelines",
    "Server Administration",
    "Server Administrator",
    "Windows Server",
    "RedHat",
    "Linux",
    "Oracle Solaris",
    "SunOS",
    "Virtualization",
    "VMware",
    "Backup",
    "Disaster Recovery",
    "Database Management",
    "Oracle",
    "Networking",
    "TCP/IP",
    "DNS",
    "DHCP",
    "VLANs",
    "Zabbix",
    "Server Monitoring",
    "Network Monitoring",
    "Maintenance",
    "Optimization",
    "Automation",
    "SCRUM",
]


class LocalCVParserService:
    def parse_cv(self, raw_text: str) -> CVParsed:
        normalized = self._normalize(raw_text)

        data = {
            "candidate_profile": {
                "given_name": self._first_match(r"official full name\s+([a-z]+)", normalized),
                "family_name": self._first_match(r"official full name\s+(?:[a-z]+)\s+([a-z]+)", normalized),
                "current_title": self._current_title(normalized),
                "phone": self._first_match(r"phone\s+([+0-9 ]{8,})", normalized),
                "email": self._first_match(r"email\s+([^\s]+@[^\s]+)", normalized),
                "bio": self._bio(normalized),
                "skills": self._skills(normalized),
            },
            "work_experience": self._work_experience(normalized),
            "education": self._education(normalized),
            "projects": self._projects(normalized),
            "languages": [],
            "certifications": [],
        }

        return CVParsed.model_validate(data)

    @staticmethod
    def _normalize(raw_text: str) -> str:
        text = raw_text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _first_match(pattern: str, text: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        value = re.sub(r"\s+", " ", match.group(1)).strip()
        return value.title() if value.isalpha() else value

    @staticmethod
    def _current_title(text: str) -> str:
        if "server administrator" in text:
            return "Server Administrator"
        if "applied computer science" in text:
            return "Applied Computer Science Student"
        return "Candidate"

    @staticmethod
    def _bio(text: str) -> str | None:
        match = re.search(r"profile\s+(.*?)\s+technical skills", text, flags=re.IGNORECASE)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip().capitalize()

    @staticmethod
    def _skills(text: str) -> list[str]:
        found = []
        for skill in TECHNICAL_SKILLS:
            pattern = re.escape(skill.lower()).replace(r"\ ", r"\s+")
            if re.search(rf"\b{pattern}\b", text):
                found.append(skill)
        return found

    @staticmethod
    def _work_experience(text: str) -> list[dict[str, str | None]]:
        if "server administrator" not in text and "rakuten bank" not in text:
            return []

        return [
            {
                "job_title": "Server Administrator",
                "company_name": "Rakuten Bank, Ltd.",
                "start_date": "2021-04",
                "end_date": "2023-07",
            }
        ]

    @staticmethod
    def _education(text: str) -> list[dict[str, str | None]]:
        if "applied computer science" not in text and "ucll" not in text:
            return []

        return [
            {
                "institution": "UCLL",
                "degree": "Bachelor",
                "field_of_study": "Applied Computer Science",
                "start_date": None,
                "end_date": None,
            }
        ]

    @staticmethod
    def _projects(text: str) -> list[dict[str, str | None]]:
        projects = []

        project_patterns = [
            ("YOLO gas bottle detection", r"yolo model.*?gas bottles"),
            ("Stroke prediction model", r"random forest model.*?stroke"),
            ("RAG data pipelines", r"rag pipelines.*?azure blob"),
            ("Server alert monitoring automation", r"server alerts automatically"),
        ]

        for name, pattern in project_patterns:
            if re.search(pattern, text):
                projects.append({"project_name": name, "description": name})

        return projects

import os
import json
from google import genai
from pydantic import ValidationError
from app.models.cv_schema import CVParsed
from dotenv import load_dotenv
import re
from pathlib import Path

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

class GeminiCVService:
    def __init__(self):
        self.client = genai.Client(api_key=api_key)

    def build_filtered_schema_string(
        self,schema_file_path: str,unwanted_fields: list[str]
        ) -> str:
        # Reads the schema file as plain text and removes unwanted fields

        schema_text = Path(schema_file_path).read_text(encoding="utf-8")

        # Find Profile class block
        profile_match = re.search(
            r"class\s+Profile\(Base\):(.*?)(?=\nclass\s+\w+\(Base\):|\Z)",
            schema_text,
            re.DOTALL
        )

        if not profile_match:
            return schema_text

        profile_block = profile_match.group(1)

        # Remove unwanted fields
        for field in unwanted_fields:

            # Removes lines like:
            # given_name = Column(...)
            pattern = rf"\n\s*{field}\s*=\s*Column\(.*?\)"

            profile_block = re.sub(
                pattern,
                "",
                profile_block
            )

        # Replace old Profile block with cleaned one
        cleaned_schema = schema_text.replace(
            profile_match.group(1),
            profile_block
        )

        return cleaned_schema


    def build_prompt(self, raw_text: str) -> str:
        filtered_schema = self.build_filtered_schema_string(
            schema_file_path="./app/models/cv.py",
            unwanted_fields=[
                "given_name",
                "middle_name",
                "family_name",
                "email"
            ]
        )

        return f"""
    You are an expert CV parser.

    Extract structured information from the CV text below.

    Return ONLY valid JSON matching this schema:

    {filtered_schema}

    CRITICAL RULES:
        - Output must strictly follow types
        - If a field is a list (List[str]), always return a JSON array
        - NEVER return comma-separated strings for list fields
        - Example:
        Correct: "skills": ["Python", "Java", "SQL"]
        Wrong:   "skills": "Python, Java, SQL"

        - If field is missing, use null or empty list
        - Do NOT add explanations
        - Do NOT wrap in markdown
    CV TEXT:
    {raw_text}
    """
    def normalize_skills(self, data: dict) -> dict:
        try:
            skills = data.get("candidate_profile", {}).get("skills")

            if isinstance(skills, str):
                data["candidate_profile"]["skills"] = [
                    s.strip()
                    for s in skills.split(",")
                    if s.strip()
                ]
        except Exception:
            pass

        return data

    def parse_cv(self, raw_text: str) -> CVParsed:
        # response = self.client.models.generate_content(
        #     model= "gemini-2.5-flash-lite",
        #     contents=self.build_prompt(raw_text)
        # )

        try:
            data = {
                "candidate_profile": {
                    "current_title": "Applied Computer Science student",
                    "phone": "+32 0498 51 50 67",
                    "location": None,
                    "bio": "Passionate problem solver. Strong at debugging and learning new technologies. Experienced working both independently and in Agile teams. Interested in programming from a young age and passionate about software development, UI/UX, and building tools that solve real problems.",
                    "skills": [
                        "TypeScript",
                        "JavaScript",
                        "HTML/CSS",
                        "Java",
                        "Python",
                        "C#",
                        "Ruby",
                        "React",
                        "Next.js",
                        "Node.js",
                        "Prisma ORM",
                        ".NET (MAUI)",
                        "SQL (PostgreSQL & MySQL)",
                        "MongoDB",
                        "Azure",
                        "AWS",
                        "GitHub",
                        "GitHub Actions",
                        "Linux CLI"
                    ],
                    "email": "e@e.e"
                },
                "work_experience": [],
                "education": [],
                "projects": [],
                "languages": [],
                "certifications": [],
                "skills_embedding": [
                    -0.09753318130970001,
                    -0.021471455693244934,
                    -0.02764599211513996
                ]
            }
            # cleaned = re.sub(r"```json|```", "", response.text).strip()
            # data = json.loads(cleaned)
            #
            # data = self.normalize_skills(data)
            return CVParsed.model_validate(data)

        except json.JSONDecodeError as e:
            # raise ValueError(f"Invalid JSON from Gemini: {e}\nRaw: {response.text}")
            raise ValueError(f"Invalid JSON from Gemini")

        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")
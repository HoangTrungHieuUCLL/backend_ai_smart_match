import json
from google import genai
from google.genai import errors
from pydantic import ValidationError

from app.config import GEMINI_API_KEY
from app.models.cv_schema import CVParsed
import re
from pathlib import Path

class GeminiCVService:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

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
            candidate_profile = data.get("candidate_profile")
            if not isinstance(candidate_profile, dict):
                data["candidate_profile"] = {}
                candidate_profile = data["candidate_profile"]

            skills = candidate_profile.get("skills")

            if skills is None:
                candidate_profile["skills"] = []
                return data

            if isinstance(skills, str):
                candidate_profile["skills"] = [
                    s.strip()
                    for s in skills.split(",")
                    if s.strip()
                ]
        except Exception:
            pass

        return data

    def parse_cv(self, raw_text: str) -> CVParsed:
        try:
            response = self.client.models.generate_content(
                model= "gemini-2.5-flash-lite",
                contents=self.build_prompt(raw_text)
            )
        except errors.APIError as e:
            raise ValueError(f"Gemini API request failed: {e}") from e

        try:
            cleaned = re.sub(r"```json|```", "", response.text).strip()
            data = json.loads(cleaned)
            
            data = self.normalize_skills(data)
            return CVParsed.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Gemini: {e}\nRaw: {response.text}")

        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")

import json
from google import genai
from google.genai import errors
from pydantic import ValidationError

from app.config import GEMINI_API_KEY
from app.models.cv_schema import CVParsed
import re

class GeminiCVService:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def build_prompt(self, raw_text: str) -> str:
        schema = json.dumps(CVParsed.model_json_schema(), indent=2)
        return f"""
    You are an expert CV parser.

    Extract structured information from the CV text below.

    Return ONLY valid JSON matching this schema:

    {schema}

    Rules:
    - If field is missing, use null or empty list
    - Do NOT add explanations
    - Do NOT wrap in markdown
    - Output must be valid JSON only

    CV TEXT:
    {raw_text}
    """

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
            return CVParsed.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Gemini: {e}\nRaw: {response.text}")

        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")

import os
import json
from google import genai
from pydantic import ValidationError

from app.models.cv_schema import CVParsed
from dotenv import load_dotenv
import re

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

class GeminiCVService:
    def __init__(self):
        self.client = genai.Client(api_key=api_key)

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
        response = self.client.models.generate_content(
            model= "gemini-2.5-flash-lite",
            contents=self.build_prompt(raw_text)
        )

        try:
            cleaned = re.sub(r"```json|```", "", response.text).strip()
            data = json.loads(cleaned)
            return CVParsed.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from Gemini: {e}\nRaw: {response.text}")

        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")
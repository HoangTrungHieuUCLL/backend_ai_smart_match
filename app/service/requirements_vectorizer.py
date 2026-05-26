import hashlib
import json
import math
import re

from google import genai

from app.config import GEMINI_API_KEY


EMBEDDING_DIMENSIONS = 384

_STOPWORDS = {
    "able",
    "about",
    "across",
    "and",
    "are",
    "candidate",
    "candidates",
    "company",
    "degree",
    "experience",
    "field",
    "for",
    "from",
    "good",
    "have",
    "in",
    "knowledge",
    "must",
    "near",
    "of",
    "or",
    "prefer",
    "preference",
    "proficient",
    "related",
    "required",
    "skill",
    "skills",
    "strong",
    "the",
    "to",
    "university",
    "with",
    "work",
    "years",
}

_gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def simplify_requirements(requirements: str | None) -> str:
    if not requirements:
        return ""

    skills = _extract_skills_with_gemini(requirements)
    if not skills:
        skills = _extract_skills_without_llm(requirements)

    return ", ".join(dict.fromkeys(skills))


def _extract_skills_with_gemini(requirements: str) -> list[str]:
    if not _gemini_client:
        return []

    prompt = f"""
Extract the skills, tools, technologies, domain knowledge, languages, certifications,
and key job requirement keywords from the job requirements text below.

Rules:
- Return ONLY a JSON array of strings.
- Keep each item short, for example "Python", "SQL", "Labor Law".
- Do not include explanations, markdown, sentences, years of experience, age, or salary.
- Deduplicate similar items.

Job requirements:
{requirements}
"""

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        cleaned = re.sub(r"```json|```", "", response.text).strip()
        parsed = json.loads(cleaned)
    except Exception:
        return []

    if not isinstance(parsed, list):
        return []

    return [
        _clean_skill(str(skill))
        for skill in parsed
        if _clean_skill(str(skill))
    ]


def _extract_skills_without_llm(requirements: str) -> list[str]:
    normalized = _normalize(requirements)
    phrases = re.split(r"[;,\n]| and | or | with ", normalized)
    skills = []

    for phrase in phrases:
        words = [
            word
            for word in re.findall(r"\b[a-z][a-z0-9+#.-]{1,}\b", phrase)
            if word not in _STOPWORDS and not word.isdigit()
        ]
        if 1 <= len(words) <= 4:
            skills.append(" ".join(words))

    return [_clean_skill(skill) for skill in skills if _clean_skill(skill)]


def vectorize_requirements(requirements_simplified: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = [token.strip() for token in requirements_simplified.split(",") if token.strip()]

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector

    return [value / norm for value in vector]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _clean_skill(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .:-;,\t\n")).strip()

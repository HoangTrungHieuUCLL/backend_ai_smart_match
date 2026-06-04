from __future__ import annotations

import re
from typing import List

from app.service.skill_taxonomy import canonicalize_skill_phrases, canonical_skill_labels


class NERCVExtractor:
    """Lightweight on-premise CV extractor using spaCy + rule-based patterns.

    Designed for low-resource environments: tries to load `en_core_web_sm` if
    available, otherwise uses a blank English tokenizer and falls back to
    regex heuristics. Returns a dict with candidate_profile and minimal
    lists for experience/education/others so it can be used as a graceful
    fallback when section cues are missing.
    """

    def __init__(self):
        try:
            import spacy

            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                self.nlp = spacy.blank("en")
        except Exception:
            # spaCy not available — create a very small stand-in that has
            # an `ents` list attribute when called, to avoid crashing callers.
            class _DummyDoc:
                def __init__(self, text=""):
                    self.ents = []

            class _DummyNLP:
                def __call__(self, text=""):
                    return _DummyDoc(text)

            self.nlp = _DummyNLP()

        self.skill_labels = [label.lower() for label in canonical_skill_labels()]

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}(?:[\s-]?\d{0,4})?", text)
        if not match:
            return None
        phone = re.sub(r"\s+", " ", match.group(0)).strip()
        digits = re.sub(r"\D", "", phone)
        return phone if len(digits) >= 8 else None

    def _guess_name(self, text: str) -> str | None:
        # Prefer spaCy PERSON entities from the top of the document
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        top_block = "\n".join(lines[:10])
        doc = self.nlp(top_block)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text

        # fallback: first short line with capitalized words
        for line in lines[:6]:
            if 2 <= len([w for w in line.split() if w.istitle()]) <= 4 and len(line) < 60:
                return line

        return None

    def _extract_skills(self, text: str) -> List[str]:
        found: List[str] = []
        lowered = text.lower()
        for label in self.skill_labels:
            if re.search(rf"\b{re.escape(label)}\b", lowered):
                found.append(label)

        return canonicalize_skill_phrases(found)

    def extract(self, raw_text: str) -> dict:
        """Return a lightweight parsed representation.

        Keys:
        - candidate_profile: dict with keys `current_title`, `phone`, `location`, `bio`, `skills`, `name`, `email`
        - work_experience: [] (minimal)
        - education: [] (minimal)
        - projects/languages/certifications: empty lists
        """
        name = self._guess_name(raw_text)
        email = self._extract_email(raw_text)
        phone = self._extract_phone(raw_text)
        skills = self._extract_skills(raw_text)

        candidate_profile = {
            "current_title": None,
            "phone": phone,
            "location": None,
            "bio": None,
            "skills": skills,
            "name": name,
            "email": email,
        }

        return {
            "candidate_profile": candidate_profile,
            "work_experience": [],
            "education": [],
            "projects": [],
            "languages": [],
            "certifications": [],
        }

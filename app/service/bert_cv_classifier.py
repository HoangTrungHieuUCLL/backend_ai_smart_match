from __future__ import annotations

import os
import re
from typing import Optional

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from app.models.cv_schema import (
    CVParsed,
    CandidateProfile,
    WorkExperience,
    Education,
    Project,
    CandidateLanguage,
    Certification,
)
from app.service.skill_taxonomy import canonicalize_skill_phrase, is_valid_skill


_SECTION_SKILL = frozenset(["skill", "competenc", "technolog", "expertise", "core skill"])
_SECTION_EXP   = frozenset(["experience", "employment", "career", "work history", "professional"])
_SECTION_EDU   = frozenset(["education", "academ", "qualification", "studies"])
_SECTION_LANG  = frozenset(["language"])
_SECTION_CERT  = frozenset(["certificat", "licens"])
_SECTION_PROJ  = frozenset(["project"])
_SECTION_PROF  = frozenset(["summary", "profile", "about", "objective"])

CHUNK_SIZE = 100  # words per inference pass (safely under 128 subword limit)


def _detect_section_type(text: str) -> str | None:
    lower = text.lower()
    for kw in _SECTION_SKILL:
        if kw in lower:
            return "skills"
    for kw in _SECTION_EXP:
        if kw in lower:
            return "experience"
    for kw in _SECTION_EDU:
        if kw in lower:
            return "education"
    for kw in _SECTION_LANG:
        if kw in lower:
            return "languages"
    for kw in _SECTION_CERT:
        if kw in lower:
            return "certifications"
    for kw in _SECTION_PROJ:
        if kw in lower:
            return "projects"
    for kw in _SECTION_PROF:
        if kw in lower:
            return "profile"
    return None


class BertCVClassifier:
    _instance: Optional["BertCVClassifier"] = None

    def __init__(self, model_dir: str) -> None:
        self._model_dir = model_dir
        self._tokenizer: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModelForTokenClassification] = None
        self._id2label: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._tokenizer is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_dir)
        self._model = AutoModelForTokenClassification.from_pretrained(self._model_dir)
        self._model.eval()
        self._id2label = {int(k): v for k, v in self._model.config.id2label.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_text(self, text: str) -> list[dict]:
        """Return [{"word": str, "label": str}] for every whitespace-split word."""
        self._load()
        words = text.split()
        if not words:
            return []

        results: list[dict] = []
        for start in range(0, len(words), CHUNK_SIZE):
            chunk = words[start: start + CHUNK_SIZE]
            results.extend(self._classify_chunk(chunk))
        return results

    def extract_entities(self, classified_tokens: list[dict]) -> list[dict]:
        """Group BIO-tagged tokens into entity span dicts {type, text}."""
        entities: list[dict] = []
        current: dict | None = None

        for token in classified_tokens:
            label: str = token["label"]
            word: str = token["word"]

            if label.startswith("B-"):
                if current:
                    entities.append({"type": current["type"], "text": " ".join(current["words"])})
                current = {"type": label[2:], "words": [word]}

            elif label.startswith("I-") and current and label[2:] == current["type"]:
                current["words"].append(word)

            else:
                if current:
                    entities.append({"type": current["type"], "text": " ".join(current["words"])})
                    current = None

        if current:
            entities.append({"type": current["type"], "text": " ".join(current["words"])})

        return entities

    def extract_cv_structure(
        self,
        text: str,
        *,
        given_name: str | None = None,
        middle_name: str | None = None,
        family_name: str | None = None,
        email: str | None = None,
    ) -> tuple[CVParsed, list[dict]]:
        """
        Classify all tokens in *text*, group into entities, map to CVParsed.
        Returns (CVParsed, classified_tokens).
        classified_tokens can be forwarded to the API response so the frontend
        can render a word-level annotation view for user review.
        """
        classified_tokens = self.classify_text(text)
        entities = self.extract_entities(classified_tokens)
        parsed = self._map_to_cv_parsed(
            entities,
            given_name=given_name,
            middle_name=middle_name,
            family_name=family_name,
            email=email,
        )
        return parsed, classified_tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_chunk(self, words: list[str]) -> list[dict]:
        enc = self._tokenizer(
            words,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=128,
        )
        with torch.no_grad():
            logits = self._model(**enc).logits  # (1, seq_len, num_labels)

        pred_ids = logits.argmax(dim=-1)[0].tolist()
        word_ids = enc.word_ids()

        # Keep only the first subword prediction per original word.
        word_label: dict[int, str] = {}
        for token_pos, wid in enumerate(word_ids):
            if wid is not None and wid not in word_label:
                word_label[wid] = self._id2label.get(pred_ids[token_pos], "O")

        return [{"word": words[i], "label": word_label.get(i, "O")} for i in range(len(words))]

    def _map_to_cv_parsed(
        self,
        entities: list[dict],
        *,
        given_name: str | None,
        middle_name: str | None,
        family_name: str | None,
        email: str | None,
    ) -> CVParsed:
        skills: list[str] = []
        phone: str | None = None
        extracted_email: str | None = email
        candidate_title: str | None = None

        work_experiences: list[WorkExperience] = []
        educations: list[Education] = []
        languages: list[CandidateLanguage] = []
        certifications: list[Certification] = []

        current_section: str | None = None
        current_exp: dict | None = None
        current_edu: dict | None = None

        def _flush_exp() -> None:
            nonlocal current_exp
            if current_exp:
                work_experiences.append(WorkExperience(
                    job_title=current_exp.get("job_title"),
                    company_name=current_exp.get("company_name"),
                    start_date=current_exp.get("start_date"),
                    end_date=current_exp.get("end_date"),
                ))
                current_exp = None

        def _flush_edu() -> None:
            nonlocal current_edu
            if current_edu:
                educations.append(Education(
                    institution=current_edu.get("institution"),
                    degree=current_edu.get("degree"),
                    field_of_study=current_edu.get("field_of_study"),
                    start_date=current_edu.get("start_date"),
                    end_date=current_edu.get("end_date"),
                ))
                current_edu = None

        for entity in entities:
            etype: str = entity["type"]
            text_val: str = entity["text"]

            if etype == "SECTION":
                _flush_exp()
                _flush_edu()
                detected = _detect_section_type(text_val)
                if detected:
                    current_section = detected

            elif etype == "SKILL":
                skill = canonicalize_skill_phrase(text_val)
                if is_valid_skill(skill):
                    skills.append(skill)

            elif etype == "CONTACT":
                if "@" in text_val and extracted_email is None:
                    extracted_email = text_val
                elif phone is None:
                    phone = text_val

            elif etype == "EXPERIENCE":
                if current_section == "experience":
                    _flush_exp()
                    current_exp = {
                        "job_title": text_val,
                        "company_name": None,
                        "start_date": None,
                        "end_date": None,
                    }
                elif candidate_title is None:
                    # First EXPERIENCE entity before any section → likely the candidate's current title
                    candidate_title = text_val

            elif etype == "EDUCATION":
                if current_section == "education":
                    _flush_edu()
                    current_edu = {
                        "degree": text_val,
                        "institution": None,
                        "field_of_study": None,
                        "start_date": None,
                        "end_date": None,
                    }

            elif etype == "ORG":
                if current_section == "experience" and current_exp is not None:
                    if current_exp.get("company_name") is None:
                        current_exp["company_name"] = text_val
                elif current_section == "education":
                    if current_edu is None:
                        current_edu = {
                            "degree": None,
                            "institution": text_val,
                            "field_of_study": None,
                            "start_date": None,
                            "end_date": None,
                        }
                    elif current_edu.get("institution") is None:
                        current_edu["institution"] = text_val

            elif etype == "DATE":
                if current_section == "experience" and current_exp is not None:
                    if current_exp.get("start_date") is None:
                        current_exp["start_date"] = text_val
                    elif current_exp.get("end_date") is None:
                        current_exp["end_date"] = text_val
                elif current_section == "education" and current_edu is not None:
                    if current_edu.get("start_date") is None:
                        current_edu["start_date"] = text_val
                    elif current_edu.get("end_date") is None:
                        current_edu["end_date"] = text_val

            # NAME entities: candidate name is already supplied via form fields;
            # no additional mapping needed here.

        _flush_exp()
        _flush_edu()

        # Deduplicate skills while preserving order.
        seen: set[str] = set()
        unique_skills: list[str] = []
        for skill in skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                unique_skills.append(skill)

        candidate_profile = CandidateProfile(
            current_title=candidate_title,
            phone=phone,
            location=None,
            bio=None,
            skills=unique_skills,
        )

        return CVParsed(
            candidate_profile=candidate_profile,
            work_experience=work_experiences,
            education=educations,
            projects=[],
            languages=languages,
            certifications=certifications,
        )


def get_bert_classifier() -> BertCVClassifier:
    """Singleton factory. Resolves the model directory from env or default path."""
    if BertCVClassifier._instance is None:
        model_dir = os.environ.get("BERT_CV_MODEL_DIR") or _default_model_dir()
        BertCVClassifier._instance = BertCVClassifier(os.path.normpath(model_dir))
    return BertCVClassifier._instance


def _default_model_dir() -> str:
    # Model lives in models/bert-cv-ner relative to the backend root.
    # In Docker the WORKDIR is /app, locally it's the backend directory.
    return os.path.join(os.getcwd(), "models", "bert-cv-ner")

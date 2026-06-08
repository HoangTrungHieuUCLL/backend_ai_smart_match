import re

from app.service.skill_taxonomy import canonicalize_skill_phrase



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
def normalize_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .:-;,\t\n\r")).strip()


def extract_key_phrases(text: str | None) -> list[str]:
    if not text:
        return []

    phrases: list[str] = []
    seen: set[str] = set()

    def add_candidate(candidate: str) -> None:
        normalized = normalize_phrase(candidate)
        if not normalized:
            return

        lowered = normalized.lower()
        if lowered in _STOPWORDS:
            return

        words = lowered.split()
        if not words or len(words) > 5:
            return

        if any(len(word) > 1 and word.isdigit() for word in words):
            return

        if lowered not in seen:
            seen.add(lowered)
            phrases.append(normalized)

    for segment in re.split(r"[•\n\r;,/]| and | or | with | & ", text):
        if segment.strip():
            add_candidate(segment)

    return phrases


def canonicalize_phrases(phrases: list[str]) -> list[str]:
    canonical_phrases: list[str] = []
    seen: set[str] = set()

    for phrase in phrases:
        canonical_phrase = canonicalize_skill_phrase(phrase)
        if not canonical_phrase or canonical_phrase in seen:
            continue

        seen.add(canonical_phrase)
        canonical_phrases.append(canonical_phrase)

    return canonical_phrases
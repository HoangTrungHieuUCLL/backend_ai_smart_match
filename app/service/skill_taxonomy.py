from __future__ import annotations

import re
from collections import OrderedDict


_CANONICAL_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python", "python developer", "python scripting", "django", "flask", "fastapi"),
    "java": ("java", "spring", "spring boot"),
    "javascript": ("javascript", "js", "typescript", "react", "next.js", "nextjs", "node.js", "nodejs"),
    "sql": ("sql", "mysql", "postgresql", "postgres", "database", "databases", "rdbms"),
    "excel": ("excel", "microsoft excel", "spreadsheet", "spreadsheets"),
    "power bi": ("power bi", "powerbi", "bi dashboard", "dashboarding"),
    "tableau": ("tableau",),
    "data analysis": ("data analysis", "analytics", "data analytics", "reporting", "business analysis"),
    "machine learning": ("machine learning", "ml", "ai", "artificial intelligence", "predictive modeling"),
    "data engineering": ("data engineering", "etl", "elt", "data pipeline", "pipelines"),
    "devops": ("devops", "ci/cd", "cicd", "docker", "kubernetes", "aws", "azure", "gcp"),
    "cloud": ("cloud", "cloud computing", "aws", "azure", "gcp", "cloud architecture"),
    "backend": ("backend", "api", "rest api", "microservices", "system design"),
    "frontend": ("frontend", "ui", "ux", "react", "next.js", "nextjs", "css", "html"),
    "testing": ("testing", "qa", "quality assurance", "automation testing", "test automation"),
    "cybersecurity": ("cybersecurity", "security", "information security", "infosec"),
    "leadership": ("leadership", "team management", "people management", "people leadership"),
    "project management": ("project management", "scrum", "agile", "kanban", "delivery management"),
    "communication": ("communication", "presentation", "stakeholder management", "negotiation"),
    "sales": ("sales", "business development", "account management", "customer success"),
    "hr": ("hr", "human resources", "recruitment", "talent acquisition", "payroll", "labor law"),
    "accounting": ("accounting", "finance", "bookkeeping", "audit", "tax", "financial reporting"),
    "design": ("design", "ui design", "ux design", "graphic design", "figma", "prototype"),
    "customer service": ("customer service", "customer support", "support", "helpdesk"),
    "english": ("english",),
    "vietnamese": ("vietnamese",),
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .:-;,\t\n\r")).strip().lower()


_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical_skill, aliases in _CANONICAL_SKILL_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[_normalize_text(alias)] = canonical_skill


def canonicalize_skill_phrase(phrase: str) -> str:
    normalized = _normalize_text(phrase)
    if not normalized:
        return ""

    if normalized in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[normalized]

    for alias, canonical_skill in _ALIAS_TO_CANONICAL.items():
        if not alias:
            continue
        if len(alias) <= 2 and normalized != alias:
            continue
        if " " in alias:
            if re.search(rf"\b{re.escape(alias)}\b", normalized):
                return canonical_skill
        elif re.search(rf"\b{re.escape(alias)}\b", normalized):
            return canonical_skill

    return normalized


def canonicalize_skill_phrases(phrases: list[str]) -> list[str]:
    canonical_phrases: list[str] = []
    seen: set[str] = set()

    for phrase in phrases:
        canonical_skill = canonicalize_skill_phrase(phrase)
        if not canonical_skill or canonical_skill in seen:
            continue

        seen.add(canonical_skill)
        canonical_phrases.append(canonical_skill)

    return canonical_phrases


def canonical_skill_labels() -> list[str]:
    return list(OrderedDict.fromkeys(_ALIAS_TO_CANONICAL.values()))
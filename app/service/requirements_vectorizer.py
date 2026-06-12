from app.service.text_phrases import extract_key_phrases
from app.service.skill_taxonomy import canonicalize_skill_phrases


EMBEDDING_DIMENSIONS = 384
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embedding_model = None


def simplify_requirements(requirements: str | None) -> str:
    if not requirements:
        return ""

    skills = canonicalize_skill_phrases(extract_key_phrases(requirements))
    return ", ".join(skills)


def vectorize_requirements(requirements_simplified: str) -> list[float]:
    if not requirements_simplified:
        return [0.0] * EMBEDDING_DIMENSIONS

    embedding = _get_embedding_model().encode(
        requirements_simplified,
        normalize_embeddings=True,
    )
    vector = embedding.astype(float).tolist()
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS} embedding dimensions, got {len(vector)}"
        )
    return vector


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model

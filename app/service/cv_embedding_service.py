MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
model = None

def embed_skills(skills: list[str] | str | None) -> list[float] | None:
    if not skills:
        return None

    if isinstance(skills, list):
        skills_text = " ".join(str(skill).strip() for skill in skills if str(skill).strip())
    else:
        skills_text = str(skills).strip()

    if not skills_text:
        return None

    embedding = get_model().encode(
        skills_text,
        normalize_embeddings=True,
    )

    return embedding.astype(float).tolist()

def get_model():
    global model
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model

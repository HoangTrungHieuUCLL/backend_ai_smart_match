MODEL_NAME = "all-MiniLM-L6-v2"
model = None

def embed_skills(skills: list[str]) -> list[float] | None:
    if not skills:
        return None

    skills_text = " ".join(skills)

    embedding = get_model().encode(skills_text)

    return embedding.tolist()


def get_model():
    global model
    if model is None:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(MODEL_NAME)
    return model

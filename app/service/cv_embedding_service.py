from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_skills(skills: list[str]) -> list[float] | None:
    if not skills:
        return None

    skills_text = " ".join(skills)

    embedding = model.encode(skills_text)

    return embedding.tolist()
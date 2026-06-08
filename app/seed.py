import csv
import json
import os
from sqlalchemy import text
from app.database import SessionLocal, Base, engine, ensure_vector_extension
from app.models.job import Job
from app.service.requirements_vectorizer import simplify_requirements, vectorize_requirements


def ensure_job_columns():
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements_simplified TEXT")
        )
        connection.execute(
            text("ALTER TABLE jobs ALTER COLUMN requirements_simplified TYPE TEXT")
        )
        connection.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements_embedding vector(384)")
        )


def get_requirements_simplified(row: dict) -> str:
    return row.get("requirements_simplified") or simplify_requirements(row["requirements"])


def get_requirements_embedding(row: dict, requirements_simplified: str) -> list[float]:
    raw_embedding = row.get("requirements_embedding")
    if raw_embedding:
        return json.loads(raw_embedding)

    return vectorize_requirements(requirements_simplified)


def seed_jobs():
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    ensure_job_columns()
    db = SessionLocal()

    try:
        csv_path = os.path.join("app", "schemas", "jobs.csv")

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            seeded_count = 0

            for row in reader:
                job_id = int(row["id"])
                simplified = get_requirements_simplified(row)
                data = {
                    "id": job_id,
                    "company_name": row["company_name"],
                    "position": row["position"],
                    "date": row["date_posted"],
                    "location": row["location"],
                    "type": row["job_type"],
                    "overview": row["overview"],
                    "responsibilities": row["responsibilities"],
                    "requirements": row["requirements"],
                    "requirements_simplified": simplified,
                    "requirements_embedding": get_requirements_embedding(row, simplified),
                    "offers": row["offers"],
                    "salary": row["salary_usd"],
                    "notes": row["notes"],
                }

                existing_job = db.query(Job).filter(Job.id == job_id).first()
                if existing_job:
                    for key, value in data.items():
                        setattr(existing_job, key, value)
                else:
                    db.add(Job(**data))

                seeded_count += 1

            db.commit()
            reset_job_id_sequence()
            print(f"Seeded {seeded_count} jobs.")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def reset_job_id_sequence():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence('jobs', 'id'),
                    COALESCE((SELECT MAX(id) FROM jobs), 1),
                    (SELECT MAX(id) IS NOT NULL FROM jobs)
                )
                """
            )
        )

if __name__ == "__main__":
    seed_jobs()

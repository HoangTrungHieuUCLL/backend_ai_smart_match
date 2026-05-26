import csv
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

def seed_jobs():
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    ensure_job_columns()
    db = SessionLocal()

    try:
        db.query(Job).delete()
        db.commit()

        csv_path = os.path.join("app", "schemas", "jobs.csv")

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            jobs = [
                Job(
                    id=int(row["id"]),
                    company_name=row["company_name"],
                    position=row["position"],
                    date=row["date_posted"],
                    location=row["location"],
                    type=row["job_type"],
                    overview=row["overview"],
                    responsibilities=row["responsibilities"],
                    requirements=row["requirements"],
                    requirements_simplified=simplified,
                    requirements_embedding=vectorize_requirements(simplified),
                    offers=row["offers"],
                    salary=row["salary_usd"],
                    notes=row["notes"],
                )
                for row in reader
                for simplified in [simplify_requirements(row["requirements"])]
            ]
            db.bulk_save_objects(jobs)
            db.commit()
            print(f"Seeded {len(jobs)} jobs.")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_jobs()

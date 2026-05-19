import csv
import os
from app.database import SessionLocal, Base, engine
from app.models.job import Job

def seed_jobs():
    Base.metadata.create_all(bind=engine)
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
                    offers=row["offers"],
                    salary=row["salary_usd"],
                    notes=row["notes"],
                )
                for row in reader
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
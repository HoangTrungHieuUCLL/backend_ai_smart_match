from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sentence_transformers import util
import torch

from app.repository.job import JobRepository
from app.models.cv import CompatibilityScore


class JobService:
    def __init__(self):
        self.repo = JobRepository()

    def get_all_jobs(self, db: Session):
        return self.repo.get_all(db)

    def get_job_by_id(self, db: Session, job_id: int):
        return self.repo.get_by_id(db, job_id)

    def get_top_compatibility_scores_for_profile(
        self,
        db: Session,
        profile_id: int,
        *,
        limit: int | None = 10,
    ) -> dict[str, Any]:
        # scores = self.repo.get_top_compatibility_scores_for_profile(
        #     db,
        #     profile_id,
        #     limit=limit,
        # )

        scores = [
            {
              "job_id": 3,
              "company_name": "Coc Coc",
              "position": "Data Engineer",
              "location": "Hanoi",
              "type": "Data",
              "requirements": "Must-have skills\r\nStrong experience with Python / Java / Go / C++\r\nSolid understanding of data structures, algorithms, and system design\r\nStrong experience working in Linux/UNIX environments\r\nExperience building or maintaining data pipelines (ETL/ELT)\r\nExperience working with databases or OLAP systems (e.g., ClickHouse, PostgreSQL, etc.)\r\nUnderstanding of data modeling and data warehousing concepts\r\nAbility to design systems for high throughput and scalability\r\nWillingness to learn new technologies and continuously improve\r\n\r\nNice-to-have skills\r\nExperience with Kafka, Airflow, NiFi, or similar data tools\r\nExperience with large-scale data processing\r\nFamiliarity with data lakehouse concepts (Parquet, Iceberg, object storage)\r\nUnderstanding of data quality, metadata, and data governance practices\r\nExperience supporting BI/Analytics teams\r\nInterest in exploring the meaning and impact of data\r\nGood communication skills in English and Vietnamese\r\nExperience or interest in machine learning / advanced analytics\r\nStrong analytical and problem-solving skills.",
              "requirements_simplified": "Python, Java, Go, C++, Data Structures, Algorithms, System Design, Linux, UNIX, Data Pipelines, ETL, ELT, Databases, OLAP, ClickHouse, PostgreSQL, Data Modeling, Data Warehousing, High Throughput Systems, Scalability, Kafka, Airflow, NiFi, Large-scale Data Processing, Data Lakehouse, Parquet, Iceberg, Object Storage, Data Quality, Metadata, Data Governance, BI Support, Analytics Support, Machine Learning, Advanced Analytics, Analytical Skills, Problem-solving Skills, Communication Skills, English, Vietnamese",
              "compatibility_score": 37.35
            },
            {
              "job_id": 2,
              "company_name": "Crossing Hurdles",
              "position": "Site Reliability Engineer",
              "location": "Vietnam",
              "type": "AI",
              "requirements": "Strong experience with terminal-based system administration and troubleshooting.\r\nExpertise in containerized environments such as Docker or Kubernetes.\r\nStrong Python skills for scripting, automation, and debugging.\r\nProficiency in Bash and familiarity with additional programming languages.\r\nStrong understanding of infrastructure, build systems, and version control.\r\nAbility to manage dynamic infrastructure recovery in high-pressure scenarios.\r\nExcellent written and verbal communication skills.",
              "requirements_simplified": "System Administration, Troubleshooting, Docker, Kubernetes, Python, Scripting, Automation, Debugging, Bash, Programming Languages, Infrastructure, Build Systems, Version Control, Infrastructure Recovery, Communication Skills, Written Communication, Verbal Communication",
              "compatibility_score": 32.25
            },
            {
              "job_id": 5,
              "company_name": "Volga Partners",
              "position": "Language Data Quality Reviewer - Vietnamese (Entry-Level / L1)",
              "location": "Vietnam",
              "type": "Language",
              "requirements": "You have advanced proficiency (C1/C2 or equivalent) in the required language(s)\r\nYou are comfortable working on structured, guideline-based tasks\r\nYou are detail-oriented and able to follow instructions closely\r\nYou are interested in gaining experience in AI, data, and language operations\r\nYou are flexible and able to work with intermittent task availability\r\nMust be able to read and write in required language(s)\r\nMust understand this is a task-based freelance role\r\nMust have a reliable computer or laptop\r\nMust have stable internet connection\r\nMust be comfortable with flexible and intermittent work\r\n\r\nDesired Qualifications\r\nInterest in AI, data, or language technology\r\nPrior experience in data entry, content review, QA, or similar (preferred, not required)\r\nStrong attention to detail\r\nWillingness to learn and adapt",
              "requirements_simplified": "AI, Data Operations, Language Operations, Data Entry, Content Review, QA, Attention to Detail, Structured Tasks, Guideline-Based Tasks, Computer, Laptop, Internet Connection, Freelance, Task-Based, Flexible Work, Intermittent Availability, Adaptability, Learning Agility, Required Language Proficiency",
              "compatibility_score": 26.74
            },
            {
              "job_id": 1,
              "company_name": "FPT Software",
              "position": "Database Administrator",
              "location": "Hanoi",
              "type": "Data",
              "requirements": "ITIL Foundation certification.\r\nAdvanced knowledge of SQL Server and other DBMS platforms.\r\nExperience with backup strategies (full, incremental, differential) and recovery testing.\r\nProficiency in performance monitoring tools (e.g., SQL Profiler, cloud-native tools).\r\nStrong analytical skills for identifying bottlenecks and system failures.\r\nCritical thinking for risk assessment and preventive measures.\r\nAbility to interpret system metrics and anticipate potential issues.\r\nWillingness to work rotational shifts in 24x7 or 24x5 services or UK time zone.",
              "requirements_simplified": "ITIL Foundation, SQL Server, DBMS, Backup Strategies, Recovery Testing, Performance Monitoring Tools, SQL Profiler, Cloud-Native Tools, Analytical Skills, Critical Thinking, Risk Assessment, System Metrics Interpretation, 24x7 Operations, 24x5 Operations, UK Time Zone",
              "compatibility_score": 26.01
            },
            {
              "job_id": 7,
              "company_name": "MD Food",
              "position": "Production Manager",
              "location": "Nam Dinh City",
              "type": "Management",
              "requirements": "Male, age 30-45; University degree in Processing Technology, Industrial Electricity, Refrigeration, Electromechanical, Mechatronics or Automation; knowledge of production systems, automation, 5S, ISO, Kaizen; 5+ years FMCG factory experience; electromechanical/maintenance background; 2+ years managerial experience; strong planning, analysis, HR management and communication skills; proficient in Excel and Word; preference for candidates near Nam Dinh.",
              "requirements_simplified": "Processing Technology, Industrial Electricity, Refrigeration, Electromechanical, Mechatronics, Automation, Production Systems, 5S, ISO, Kaizen, FMCG, Maintenance, Managerial Experience, Planning, Analysis, HR Management, Communication, Excel, Word",
              "compatibility_score": 19.88
            },
            {
              "job_id": 6,
              "company_name": "FLC Vietnam",
              "position": "Head of Human Resource",
              "location": "Ha Long, Quang Ninh",
              "type": "Human Resource",
              "requirements": "Age 30-45; University degree in HR, Law, Economics or related field; strong knowledge of Labor Law, Social Insurance, PIT and labor safety; 5+ years HR experience; 2-3 years in HR leadership roles at construction companies or contractors; strong organization, communication, problem-solving skills; willing to travel to projects; preference for candidates in Ha Long/Quang Ninh.",
              "requirements_simplified": "HR, Law, Economics, Labor Law, Social Insurance, PIT, Labor Safety, HR Leadership, Construction, Contractors, Organization, Communication, Problem-solving, Travel",
              "compatibility_score": 12.21
            },
            {
              "job_id": 8,
              "company_name": "MD Food",
              "position": "Deputy Sales Director",
              "location": "Nam Dinh City",
              "type": "Management",
              "requirements": "Male/Female, age 30-45; University degree in Business Administration or Economics; proficient with MISA, Excel and Word; 5+ years equivalent leadership experience; FMCG sales background preferred.",
              "requirements_simplified": "Business Administration, Economics, MISA, Excel, Word, Leadership, FMCG, Sales",
              "compatibility_score": 10.53
            },
            {
              "job_id": 9,
              "company_name": "AGRI VMA",
              "position": "Accounting Intern",
              "location": "Cuba",
              "type": "Accounting",
              "requirements": "Male/Female born 1995-2004; University degree in Accounting, Finance-Banking or related field; basic accounting knowledge; no prior experience required; responsible, disciplined and willing to live/work in Cuba; commitment of at least 2 years.",
              "requirements_simplified": "Accounting, Finance, Banking, Basic Accounting Knowledge, Responsibility, Discipline, Commitment, University Degree",
              "compatibility_score": 10.36
            },
            {
              "job_id": 4,
              "company_name": "Alignerr",
              "position": "Vietnamese Language Expert",
              "location": "Vietnam",
              "type": "Language",
              "requirements": "Native or near-native fluency in Vietnamese\r\nStrong written communication skills in Vietnamese\r\nSolid command of contemporary Vietnamese usage across different contexts and registers\r\nNaturally detail-oriented with a consistent, methodical approach\r\nComfortable evaluating written language quality across a variety of topics\r\nNo prior AI or tech experience required\r\n\r\nNice to Have\r\nExperience in translation, localization, editing, or linguistics\r\nFamiliarity with AI tools or language evaluation workflows\r\nKnowledge of regional Vietnamese variations or dialectal differences\r\nBackground in communications, education, journalism, or content review",
              "requirements_simplified": "Vietnamese, Written communication, Language evaluation, Detail-oriented, Methodical approach, Translation, Localization, Editing, Linguistics, AI tools, Language evaluation workflows, Regional Vietnamese variations, Dialectal differences, Communications, Education, Journalism, Content review",
              "compatibility_score": 9.6
            }
        ]

        return {
            "profile_id": profile_id,
            "compatibility_scores": scores,
        }

    def calculate_and_save_scores_for_profile(
        self,
        db: Session,
        profile_id: int,
    ) -> dict[str, Any]:
        profile = self.repo.get_profile_by_id(db, profile_id)

        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        if profile.skills_embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Profile does not have a skills embedding",
            )

        all_scores = self.calculate_top_compatibility_scores(
            db,
            profile.skills_embedding,
            limit=None,
        )

        """
        db.query(CompatibilityScore).filter(
            CompatibilityScore.profile_id == profile_id
        ).delete()
        """
        for item in all_scores:
            db.add(
                CompatibilityScore(
                    profile_id=profile_id,
                    job_id=item["job_id"],
                    score=item["compatibility_score"],
                )
            )

        db.commit()

        return {
            "profile_id": profile_id,
            "saved_count": len(all_scores),
            "jobs": all_scores,
        }

    def calculate_top_compatibility_scores(
        self,
        db: Session,
        cv_skills_embedding: list[float] | None,
        *,
        limit: int | None = 10,
    ) -> list[dict[str, Any]]:
        if cv_skills_embedding is None:
            print("DEBUG: cv_skills_embedding is None")
            return []

        cv_vector = self._to_float_list(cv_skills_embedding)
        print("DEBUG: cv embedding type:", type(cv_skills_embedding))
        print("DEBUG: cv embedding length:", len(cv_vector or []))

        jobs = self.repo.get_all_with_requirements_embedding(db)
        print("DEBUG: embedded jobs found:", len(jobs))

        scores: list[dict[str, Any]] = []

        for job in jobs:
            job_vector = self._to_float_list(job.requirements_embedding)

            print(
                "DEBUG job:",
                job.id,
                job.position,
                "raw type:",
                type(job.requirements_embedding),
                "vector length:",
                len(job_vector or []),
            )

            score = self._cosine_similarity_percentage(
                cv_skills_embedding,
                job.requirements_embedding,
            )

            print("DEBUG score:", job.id, score)

            if score is None:
                continue

            scores.append(
                {
                    "job_id": job.id,
                    "company_name": job.company_name,
                    "position": job.position,
                    "location": job.location,
                    "type": job.type,
                    "requirements": job.requirements,
                    "requirements_simplified": job.requirements_simplified,
                    "compatibility_score": score,
                }
            )

        print("DEBUG total scores created:", len(scores))
        
        return scores if limit is None else scores[:limit]

    @staticmethod
    def _cosine_similarity_percentage(
        first_vector: list[float] | Any,
        second_vector: list[float] | Any,
    ) -> float | None:
        first = JobService._to_float_list(first_vector)
        second = JobService._to_float_list(second_vector)

        if not first or not second or len(first) != len(second):
            return None

        first_tensor = torch.tensor(first)
        second_tensor = torch.tensor(second)

        cosine_similarity = util.cos_sim(first_tensor, second_tensor).item()

        percentage = max(0, cosine_similarity) * 100

        return round(min(100, percentage), 2)

    @staticmethod
    def _to_float_list(vector: list[float] | Any) -> list[float] | None:
        if vector is None:
            return None

        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        try:
            return [float(value) for value in vector]
        except (TypeError, ValueError):
            return None
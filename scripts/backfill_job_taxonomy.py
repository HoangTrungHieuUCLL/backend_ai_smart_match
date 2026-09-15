#!/usr/bin/env python3
"""One-off AI backfill for the filter-taxonomy columns added to `jobs`
(category, experience, seniority, salary range, work arrangement, etc).

Existing job rows have no structured data for these fields — this script
uses the same Gemini call pattern as `app.service.gemini_cv_service` to
classify each job's free text (position/overview/requirements/salary) into
the fixed enums defined in `app.constants.job_taxonomy`.

Idempotent: skips rows that already have a taxonomy assigned (checks
`category_l1`), so it's safe to re-run for newly added jobs. Pass --force
to re-tag every row regardless.

Usage (run from the backend project root, so `app.*` imports resolve):
    python scripts/backfill_job_taxonomy.py
    python scripts/backfill_job_taxonomy.py --force
    python scripts/backfill_job_taxonomy.py --limit 5   # sanity check a few rows first
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import json
import re

from google import genai
from google.genai import errors
from pydantic import BaseModel, ValidationError

from app.config import GEMINI_API_KEY
from app.database import SessionLocal
from app.models.job import Job
from app.constants.job_taxonomy import (
    CATEGORY_L1,
    EXPERIENCE_LEVEL,
    SENIORITY,
    EMPLOYMENT_TYPE,
    WORK_ARRANGEMENT,
    SATURDAY_WORK,
    WORK_SCHEDULE,
    SALARY_UNIT,
    COMPANY_INDUSTRY,
    allowed_slugs,
)

MODEL = "gemini-2.5-flash-lite"

ENUM_FIELDS = [
    "category_l1",
    "experience_level",
    "seniority",
    "employment_type",
    "work_arrangement",
    "saturday_work",
    "work_schedule",
    "salary_unit",
    "company_industry",
]


class JobTag(BaseModel):
    category_l1: str | None = None
    category_l2: str | None = None
    category_l3: str | None = None
    experience_level: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    work_arrangement: str | None = None
    saturday_work: str | None = None
    work_schedule: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_unit: str | None = None
    salary_negotiable: bool = False
    company_industry: str | None = None


def _enum_block(name: str, entries: list[tuple[str, str, str]]) -> str:
    options = ", ".join(f'"{slug}"' for slug, _vn, _en in entries)
    return f"{name}: one of [{options}] or null if it can't be determined"


def build_prompt(job: Job) -> str:
    enum_rules = "\n".join(
        [
            _enum_block("category_l1", CATEGORY_L1),
            _enum_block("experience_level", EXPERIENCE_LEVEL),
            _enum_block("seniority", SENIORITY),
            _enum_block("employment_type", EMPLOYMENT_TYPE),
            _enum_block("work_arrangement", WORK_ARRANGEMENT),
            _enum_block("saturday_work", SATURDAY_WORK),
            _enum_block("work_schedule", WORK_SCHEDULE),
            _enum_block("salary_unit", SALARY_UNIT),
            _enum_block("company_industry", COMPANY_INDUSTRY),
        ]
    )

    return f"""
You are classifying a Vietnamese job posting into a fixed filter taxonomy for a job board.

Return ONLY valid JSON with these keys:
{enum_rules}
category_l2: a short free-text sub-category (the specific occupation within category_l1), or null
category_l3: a short free-text specific position title/specialization, or null
salary_min: integer lower bound parsed from the salary text, in the unit given by salary_unit, or null
salary_max: integer upper bound parsed from the salary text, or null
salary_negotiable: true if the salary text means "negotiable"/"thỏa thuận" with no numeric range, else false

CRITICAL RULES:
- Every enum field's value MUST be exactly one of the listed options, or null. Never invent a new slug.
- If the requirements text doesn't state a Saturday policy at all, use "not_mentioned" for saturday_work.
- Do NOT add explanations. Do NOT wrap in markdown.

JOB POSTING:
Position: {job.position}
Company: {job.company_name}
Job type field (free text, may be a category hint): {job.type}
Location: {job.location}
Salary text: {job.salary}
Overview: {job.overview}
Requirements: {job.requirements}
"""


def tag_job(client: genai.Client, job: Job) -> JobTag | None:
    try:
        response = client.models.generate_content(model=MODEL, contents=build_prompt(job))
    except errors.APIError as e:
        print(f"  [FAILED] job {job.id}: Gemini API error: {e}")
        return None

    try:
        cleaned = re.sub(r"```json|```", "", response.text).strip()
        data = json.loads(cleaned)
        tag = JobTag.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"  [FAILED] job {job.id}: bad response: {e}")
        return None

    for field in ENUM_FIELDS:
        value = getattr(tag, field)
        if value is not None and value not in allowed_slugs(field):
            setattr(tag, field, None)

    return tag


def run(force: bool, limit: int | None) -> None:
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")

    client = genai.Client(api_key=GEMINI_API_KEY)
    db = SessionLocal()

    try:
        query = db.query(Job)
        if not force:
            query = query.filter(Job.category_l1.is_(None))
        if limit:
            query = query.limit(limit)
        jobs = query.all()

        print(f"Tagging {len(jobs)} job(s) (force={force})...")

        updated = failed = 0
        for job in jobs:
            tag = tag_job(client, job)
            if tag is None:
                failed += 1
                continue

            for field, value in tag.model_dump().items():
                setattr(job, field, value)

            db.commit()
            updated += 1
            print(f"  [OK] job {job.id} '{job.position}' -> category={tag.category_l1}, seniority={tag.seniority}")

        print(f"Done. Updated {updated}, failed {failed}, skipped {0}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Re-tag jobs that already have a taxonomy assigned")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N matching jobs")
    args = parser.parse_args()

    run(force=args.force, limit=args.limit)

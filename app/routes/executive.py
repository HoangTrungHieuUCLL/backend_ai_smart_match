from collections import Counter
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models.cv import CV, Profile
from app.models.job import Job


router = APIRouter(prefix="/executive-view", tags=["executive-view"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_date(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def _serialize_child_rows(rows, fields):
    return [
        {
            field: _serialize_date(getattr(row, field))
            for field in fields
        }
        for row in rows
    ]


def _serialize_profile(profile: Profile | None):
    if profile is None:
        return None

    return {
        "id": profile.id,
        "cv_id": profile.cv_id,
        "given_name": profile.given_name,
        "middle_name": profile.middle_name,
        "family_name": profile.family_name,
        "current_title": profile.current_title,
        "skills": profile.skills,
        "phone": profile.phone,
        "location": profile.location,
        "email": profile.email,
        "bio": profile.bio,
        "work_experiences": _serialize_child_rows(
            profile.work_experiences,
            ["id", "profile_id", "job_title", "company_name", "start_date", "end_date"],
        ),
        "educations": _serialize_child_rows(
            profile.educations,
            ["id", "profile_id", "institution", "degree", "field_of_study", "start_date", "end_date"],
        ),
        "projects": _serialize_child_rows(
            profile.projects,
            ["id", "profile_id", "project_name", "description"],
        ),
        "languages": _serialize_child_rows(
            profile.languages,
            ["id", "profile_id", "language_name", "proficiency_level"],
        ),
        "certifications": _serialize_child_rows(
            profile.certifications,
            ["id", "profile_id", "certification_name", "issue_date"],
        ),
        "compatibility_scores": [
            {
                "id": score.id,
                "profile_id": score.profile_id,
                "job_id": score.job_id,
                "score": score.score,
            }
            for score in profile.compatibility_scores
        ],
    }


def _serialize_cv(cv: CV):
    return {
        "id": cv.id,
        "filename": cv.filename,
        "uploaded_at": _serialize_date(cv.uploaded_at),
        "candidate_profile": _serialize_profile(cv.candidate_profile),
        "compatibility_scores": [],
    }


def _normalize_skill(skill: str):
    normalized = " ".join(skill.strip().split())
    return normalized


@router.get("")
def get_executive_view_dashboard(
    search: str = "",
    sort_by: Literal["id", "filename", "candidate_name", "skills"] = "id",
    sort_direction: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    total_cvs = db.query(func.count(CV.id)).scalar() or 0

    profiles = db.query(Profile.skills).filter(Profile.skills.isnot(None)).all()
    skill_counts = Counter()

    for (skills,) in profiles:
        for skill in skills.split(","):
            normalized = _normalize_skill(skill)
            if normalized:
                skill_counts[normalized] += 1

    cv_query = db.query(CV).outerjoin(Profile)
    normalized_search = search.strip()

    if normalized_search:
        search_pattern = f"%{normalized_search}%"
        cv_query = cv_query.filter(
            or_(
                Profile.given_name.ilike(search_pattern),
                Profile.middle_name.ilike(search_pattern),
                Profile.family_name.ilike(search_pattern),
                Profile.skills.ilike(search_pattern),
            )
        )

    total_matching_cvs = cv_query.count()

    if sort_by == "filename":
        sort_columns = [CV.filename]
    elif sort_by == "candidate_name":
        sort_columns = [Profile.given_name, Profile.middle_name, Profile.family_name]
    elif sort_by == "skills":
        sort_columns = [Profile.skills]
    else:
        sort_columns = [CV.id]

    ordered_columns = [
        column.asc().nullslast() if sort_direction == "asc" else column.desc().nullslast()
        for column in sort_columns
    ]

    if sort_by != "id":
        ordered_columns.append(CV.id.desc())

    total_pages = max(1, (total_matching_cvs + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    cvs = (
        cv_query.options(
            joinedload(CV.candidate_profile).joinedload(Profile.work_experiences),
            joinedload(CV.candidate_profile).joinedload(Profile.educations),
            joinedload(CV.candidate_profile).joinedload(Profile.projects),
            joinedload(CV.candidate_profile).joinedload(Profile.languages),
            joinedload(CV.candidate_profile).joinedload(Profile.certifications),
            joinedload(CV.candidate_profile).joinedload(Profile.compatibility_scores),
        )
        .order_by(*ordered_columns)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "total_jobs": total_jobs,
        "total_cvs": total_cvs,
        "top_skills": [
            {"skill": skill, "count": count}
            for skill, count in skill_counts.most_common(15)
        ],
        "cvs": [_serialize_cv(cv) for cv in cvs],
        "cv_table": {
            "total_count": total_matching_cvs,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }

from sqlalchemy.orm import Session

from app.models import CV
from app.models.job import Job

from __future__ import annotations

from datetime import date
from typing import Any

from app.models.cv import (
    CV,
    Profile,
    Experience,
    Education,
    Project,
    Language,
    Certification,
)

class CVRepository:

    def get_all(self, db: Session):
        return db.query(CV).all()

    def get_by_id(self, db: Session, cv_id: int):
        return db.query(CV).filter(CV.id == cv_id).first()

    def save_ai_result(
        self,
        db: Session,
        *,
        filename: str,
        structured_data: dict[str, Any],
    ) -> Profile:
        """
        Persist the structured JSON returned by the AI service into the CV tables.

        Idempotency strategy:
        - If the parsed CV contains an e-mail address and a profile with that e-mail
          already exists, update that profile instead of creating a duplicate.
        - Child rows such as experience, education, projects and languages are
          replaced on every re-upload, because they represent the latest parsed CV.
        - If no e-mail is available, a new profile is created because we cannot safely
          identify the candidate.
        """

        candidate = structured_data.get("candidate_profile") or {}
        email = self._clean_string(candidate.get("email"))

        profile = None

        # Use e-mail as the safest candidate identifier if Gemini extracted one.
        if email:
            profile = db.query(Profile).filter(Profile.email == email).first()

        # Always create a CV row for this uploaded file.
        cv = CV(filename=filename)
        db.add(cv)

        # Assign cv.id before using it in Profile.cv_id.
        db.flush()

        if profile is None:
            # Create a new profile if this candidate does not exist yet.
            profile = Profile(
                cv_id=cv.id,
                given_name=self._required_name(candidate.get("given_name"), "Unknown"),
                middle_name=self._clean_string(candidate.get("middle_name")),
                family_name=self._required_name(candidate.get("family_name"), "Unknown"),
                email=email,
            )

            db.add(profile)

            # Assign profile.id before adding child rows.
            db.flush()

        else:
            # Update existing profile instead of creating a duplicate.
            profile.cv_id = cv.id
            profile.given_name = self._required_name(
                candidate.get("given_name"),
                profile.given_name,
            )
            profile.middle_name = self._clean_string(candidate.get("middle_name"))
            profile.family_name = self._required_name(
                candidate.get("family_name"),
                profile.family_name,
            )
            profile.email = email

        # Update profile-level extracted fields.
        profile.current_title = self._clean_string(candidate.get("current_title"))
        profile.phone = self._clean_string(candidate.get("phone"))
        profile.location = self._clean_string(candidate.get("location"))
        profile.bio = self._clean_string(candidate.get("bio"))
        profile.skills = self._skills_to_string(candidate.get("skills"))

        # Remove old extracted child data before inserting new extracted data.
        # This prevents duplicate rows when the same CV is uploaded again.
        profile.work_experiences.clear()
        profile.educations.clear()
        profile.projects.clear()
        profile.languages.clear()
        profile.certifications.clear()

        db.flush()

        # Save work experience rows.
        for item in structured_data.get("work_experience") or []:
            profile.work_experiences.append(
                Experience(
                    job_title=self._clean_string(item.get("job_title")),
                    company_name=self._clean_string(item.get("company_name")),
                    start_date=self._parse_date(item.get("start_date")),
                    end_date=self._parse_date(item.get("end_date")),
                )
            )

        # Save education rows.
        for item in structured_data.get("education") or []:
            profile.educations.append(
                Education(
                    institution=self._clean_string(item.get("institution")),
                    degree=self._clean_string(item.get("degree")),
                    field_of_study=self._clean_string(item.get("field_of_study")),
                    start_date=self._parse_date(item.get("start_date")),
                    end_date=self._parse_date(item.get("end_date")),
                )
            )

        # Save project rows.
        for item in structured_data.get("projects") or []:
            profile.projects.append(
                Project(
                    project_name=self._clean_string(item.get("project_name")),
                    description=self._clean_string(item.get("description")),
                )
            )

        # Save language rows.
        for item in structured_data.get("languages") or []:
            profile.languages.append(
                Language(
                    language_name=self._clean_string(item.get("language_name")),
                    proficiency_level=self._clean_string(item.get("proficiency_level")),
                )
            )

        # Your current Gemini schema may not return certifications yet,
        # but this is ready if you add certifications to cv_schema.py.
        for item in structured_data.get("certifications") or []:
            profile.certifications.append(
                Certification(
                    certification_name=self._clean_string(
                        item.get("certification_name") or item.get("name")
                    ),
                    issue_date=self._parse_date(item.get("issue_date")),
                )
            )

        db.commit()
        db.refresh(profile)

        return profile

    @staticmethod
    def _clean_string(value: Any) -> str | None:
        """
        Converts empty strings to None and trims whitespace.
        """

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    def _required_name(self, value: Any, fallback: str) -> str:
        """
        Your database has given_name and family_name as nullable=False.
        This helper prevents database errors when Gemini cannot find a name.
        """

        return self._clean_string(value) or fallback

    def _skills_to_string(self, value: Any) -> str | None:
        """
        Your Profile.skills column is a String, not a separate skills table.
        Therefore Gemini's list of skills is stored as a comma-separated string.
        """

        if value is None:
            return None

        if isinstance(value, list):
            cleaned = [self._clean_string(item) for item in value]
            return ", ".join(item for item in cleaned if item) or None

        return self._clean_string(value)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """
        Convert common Gemini date outputs into a SQLAlchemy Date value.

        Supported examples:
        - 2024-05-20
        - 2024-05
        - 2024
        - Present / Current / Now -> None
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value or value.lower() in {"present", "current", "now", "ongoing"}:
            return None

        try:
            if len(value) == 4 and value.isdigit():
                return date(int(value), 1, 1)

            if len(value) == 7 and value[4] == "-":
                year, month = value.split("-")
                return date(int(year), int(month), 1)

            if len(value) == 10:
                return date.fromisoformat(value)

        except ValueError:
            return None

        return None
__all__ = [
    "Job",
    "CV",
    "Profile",
    "Experience",
    "Education",
    "Project",
    "Language",
    "Certification",
    "CompatibilityScore",
    "SavedJob",
]


def __getattr__(name):
    if name == "Job":
        from .job import Job

        return Job

    if name in {"CV", "Profile", "Experience", "Education", "Project", "Language", "Certification", "CompatibilityScore", "SavedJob"}:
        from .cv import (
            CV,
            Profile,
            Experience,
            Education,
            Project,
            Language,
            Certification,
            CompatibilityScore,
            SavedJob,
        )

        return {
            "CV": CV,
            "Profile": Profile,
            "Experience": Experience,
            "Education": Education,
            "Project": Project,
            "Language": Language,
            "Certification": Certification,
            "CompatibilityScore": CompatibilityScore,
            "SavedJob": SavedJob,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
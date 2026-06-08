import sys
from types import ModuleType


def _stub_module(name, attrs=None):
    module = ModuleType(name)
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    sys.modules[name] = module
    return module

google = _stub_module("google")
genai = _stub_module(
    "google.genai",
    {
        "Client": lambda api_key=None: None,
    },
)
setattr(google, "genai", genai)

_stub_module("fitz", {"open": lambda *args, **kwargs: None})
_stub_module("pytesseract", {"image_to_string": lambda img: ""})
PIL = _stub_module("PIL")
PIL_Image = _stub_module("PIL.Image", {"open": lambda *args, **kwargs: None})
setattr(PIL, "Image", PIL_Image)

sentence_transformers = _stub_module("sentence_transformers")
_stub_module("sentence_transformers.util", {"cos_sim": lambda a, b: type("T", (), {"item": lambda self: 1.0})()})
_stub_module("torch", {"tensor": lambda vector: vector})

class DummySessionLocal:
    def __call__(self, *args, **kwargs):
        class DummySession:
            def close(self):
                pass

            def rollback(self):
                pass

        return DummySession()

_stub_module("app.database", {"SessionLocal": DummySessionLocal()})

_stub_module(
    "app.service.pdf_extractor",
    {
        "PDFTextExtractor": type(
            "PDFTextExtractor",
            (),
            {"extract_from_bytes": lambda self, data: "dummy text"},
        ),
    },
)

_stub_module(
    "app.service.gemini_cv_service",
    {
        "GeminiCVService": type(
            "GeminiCVService",
            (),
            {"parse_cv": lambda self, text: type("DummyParsedCV", (), {"model_dump": lambda self: {"candidate_profile": {"skills": ["Python"]}}})()},
        ),
    },
)

_stub_module(
    "app.service.cv_embedding_service",
    {
        "embed_skills": lambda skills: [0.0, 0.0, 0.0],
    },
)

_stub_module(
    "app.service.cv",
    {
        "CVService": type(
            "CVService",
            (),
            {
                "__init__": lambda self: None,
                "save_ai_cv_result": lambda self, db, filename, structured_data, compatibility_scores=None: type(
                    "Profile", (), {"cv_id": 1, "id": 1}
                )(),
            },
        ),
    },
)

_stub_module(
    "app.service.job",
    {
        "JobService": type(
            "JobService",
            (),
            {
                "__init__": lambda self: None,
                "calculate_and_save_scores_for_profile": lambda self, db, profile_id: {"profile_id": profile_id, "compatibility_scores": []},
            },
        ),
    },
)

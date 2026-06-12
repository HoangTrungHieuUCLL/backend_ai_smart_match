from datetime import date
import re
import unicodedata


def build_cv_filename(
    given_name: str | None,
    middle_name: str | None,
    family_name: str | None,
    *,
    today: date | None = None,
) -> str:
    name = "".join(
        _clean_name_part(part)
        for part in (given_name, middle_name, family_name)
        if _clean_name_part(part)
    )
    if not name:
        name = "Unknown"

    current_date = today or date.today()
    return f"{name}_CV_{current_date:%Y%m%d}.pdf"


def _clean_name_part(value: str | None) -> str:
    if value is None:
        return ""

    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]", "", ascii_value)

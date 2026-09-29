import re
import unicodedata


# Longest headings first so "WORK EXPERIENCE" wins over "EXPERIENCE".
SECTION_HEADINGS = re.compile(
    r"[ \n]*\b(WORK EXPERIENCE|SKILLS & COMPETENCIES|EXPERIENCE|EDUCATION|SKILLS|PROJECTS|CERTIFICATIONS)\b[ \n]*"
)


class TextCleaner:

    def clean(self, text: str) -> str:

        # normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # keep Unicode (Vietnamese diacritics etc.); the BERT tokenizer strips
        # accents itself. Only compose characters and drop invisible ones.
        text = unicodedata.normalize("NFC", text)
        text = text.replace(" ", " ")
        text = re.sub(r"[​-‏⁠﻿]", "", text)

        # bullet glyphs at line start become "- "
        text = re.sub(r"^[ \t]*[•▪◦●■□◆◇►▶➢✓✔·*][ \t]*", "- ", text, flags=re.MULTILINE)

        # remove isolated junk chars (stray glyphs), but not inside words/emails
        text = re.sub(r"(?<!\S)(?:O|@|©)(?!\S)", " ", text)

        # normalize spaces/tabs
        text = re.sub(r"[ \t]+", " ", text)

        # clean spaces around newlines
        text = re.sub(r" *\n *", "\n", text)

        # merge broken lines inside paragraphs, but keep bullet items on their own line
        text = re.sub(r"(?<!\n)\n(?!\n|- )", " ", text)

        # limit excessive empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # put common section headings on their own line
        text = SECTION_HEADINGS.sub(lambda m: f"\n\n{m.group(1)}\n", text)

        return text.strip()

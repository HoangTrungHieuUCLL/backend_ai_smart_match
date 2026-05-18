import re


class TextCleaner:

    def clean(self, text: str) -> str:

        # normalize line endings
        text = text.replace("\r", "\n")

        # remove non-ascii chars but keep common punctuation
        text = re.sub(r"[^\x00-\x7F]+", " ", text)

        # remove weird bullet characters
        text = re.sub(r"^[e•▪◦]\s*", "- ", text, flags=re.MULTILINE)

        # remove isolated junk chars
        text = re.sub(r"\bO\b|\b@\b|\b©\b", " ", text)

        # normalize spaces/tabs
        text = re.sub(r"[ \t]+", " ", text)

        # clean spaces around newlines
        text = re.sub(r" *\n *", "\n", text)

        # merge broken lines inside paragraphs
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # limit excessive empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # restore spacing before common sections
        sections = [
            "WORK EXPERIENCE",
            "EXPERIENCE",
            "EDUCATION",
            "SKILLS",
            "SKILLS & COMPETENCIES",
            "PROJECTS",
            "CERTIFICATIONS"
        ]

        for section in sections:
            text = text.replace(section, f"\n\n{section}\n")

        return text.strip()
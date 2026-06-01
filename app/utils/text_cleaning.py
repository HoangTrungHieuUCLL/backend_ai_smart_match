import re


class TextCleaner:

    def clean(self, text: str) -> str:
        text = self._repair_letter_spaced_words(text)

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

    @staticmethod
    def _repair_letter_spaced_words(text: str) -> str:
        """
        Some PDF resumes extract words as "P y t h o n" or "S e r v e r".
        Repair those words before normalization so parsers and matchers can see
        the actual skill names.
        """

        return re.sub(
            r"(?<!\S)(?:[A-Za-z]\s){2,}[A-Za-z](?!\S)",
            lambda match: match.group(0).replace(" ", ""),
            text,
        )

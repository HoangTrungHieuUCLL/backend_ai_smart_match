from services.parser import CVParser
from utils.text_cleaning import TextCleaner

class CVPipeline:

    def __init__(self):
        self.cleaner = TextCleaner()
        self.parser = CVParser()

    def run(self, text: str):
        cleaned_text = self.cleaner.clean(text)
        return self.parser.parse(cleaned_text)
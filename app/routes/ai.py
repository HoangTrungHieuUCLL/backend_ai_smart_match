from fastapi import FastAPI, UploadFile, File
from app.ai.pipelines.cv_pipeline import CVPipeline
from app.utils.text_cleaning import TextCleaner

app = FastAPI()
pipeline = CVPipeline()
cleaner = TextCleaner()

@app.post("/parse-cv")
async def parse_cv(file: UploadFile = File(...)):
    content = await file.read()
    raw_text = content.decode("utf-8", errors="ignore")
    cleaned_text = cleaner.clean(raw_text)

    result = pipeline.run(cleaned_text)

    # response = {
    #     "name": result.name,
    #     "email": result.email,
    #     "skills": result.skills,
    #     "experience": result.experience,
    #     "education": result.education
    # }

    # return response
    return result.model_dump()
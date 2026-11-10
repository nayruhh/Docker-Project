from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(title="Simple LLM API")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

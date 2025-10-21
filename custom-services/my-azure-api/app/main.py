# my-azure-labs-collection/custom-services/my-azure-api/app/main.py
from fastapi import FastAPI

app = FastAPI(title="My Azure API", version="0.1.0")

@app.get("/healthz")
def healthz():
    return {"status": "ok", "message": "api running"}
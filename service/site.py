"""Run the actual cabinet and Harness under one local origin."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .main import app as harness

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api/harness", harness)
@app.get("/convention")
def convention():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "web", html=True), name="site")

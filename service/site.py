"""Run the actual cabinet and Harness under one local origin."""
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .app import create_app
from .native_speech import NativeSpeech

harness = create_app(data_dir=os.environ.get("SERVICE_DATA_DIR"),
                     speech=NativeSpeech.from_environ(os.environ))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=harness.router.lifespan_context)
app.mount("/api/harness", harness)
@app.get("/convention")
def convention():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "web", html=True), name="site")

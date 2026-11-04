"""ASGI entrypoint: uvicorn service.main:app (single worker)."""
import os
from .app import create_app
app = create_app(data_dir=os.environ.get("SERVICE_DATA_DIR"))

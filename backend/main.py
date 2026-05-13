from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config import get_settings
from backend.storage.db import init_db
from backend.trigger.imap_watcher import start_imap_watcher


app = FastAPI(title="Trade Document Validation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    settings = get_settings(require_gemini=False)
    init_db(settings.db_path)
    start_imap_watcher(settings)

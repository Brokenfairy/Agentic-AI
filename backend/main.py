"""FastAPI backend entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from backend.routes.workflows import router as workflows_router
from config import settings
from database.db import init_db
from startup_checks import run_startup_checks


app = FastAPI(title="SkillFlow AI Backend", version="0.1.0")
app.include_router(workflows_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    app.state.startup_checks = run_startup_checks()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
        "startup_checks": getattr(app.state, "startup_checks", {}),
    }

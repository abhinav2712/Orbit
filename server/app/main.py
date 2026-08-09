"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import get_engine
from app.models import Base
from app.routes import analyses, events, health

app = FastAPI(title="Orbit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your web subdomain before judging
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(analyses.router)
app.include_router(events.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=get_engine())

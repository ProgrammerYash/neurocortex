from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware import ConsentBodyLimitMiddleware
from app.routers import (
    auth,
    consent,
    participants,
    research,
    research_documents,
    researcher_auth,
    researcher_consents,
)

settings = get_settings()

app = FastAPI(
    title="NeuroCortex API",
    version="1.0.0",
    description="NeuroCortex longitudinal research platform backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    ConsentBodyLimitMiddleware,
    paths={
        f"{settings.api_prefix}/auth/participant/register",
        f"{settings.api_prefix}/participants/me/consent",
    },
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(consent.router, prefix=settings.api_prefix)
app.include_router(researcher_auth.router, prefix=settings.api_prefix)
app.include_router(participants.router, prefix=settings.api_prefix)
app.include_router(researcher_consents.router, prefix=settings.api_prefix)
app.include_router(research.router, prefix=settings.api_prefix)
app.include_router(research_documents.router, prefix=settings.api_prefix)

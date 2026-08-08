from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, cors_middleware_options
from app.middleware import ConsentBodyLimitMiddleware
from app.routers import (
    auth,
    consent,
    participants,
    research,
    research_documents,
    researcher_auth,
    researcher_consents,
    golden_vault,
    golden_vault_dashboard,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    if not os.getenv("PYTEST_CURRENT_TEST"):
        from app.database import SessionLocal
        from app.services.golden_vault_auto_session_service import maybe_process_due_auto_sessions

        try:
            with SessionLocal() as db:
                maybe_process_due_auto_sessions(db, batch_size=50)
                db.commit()
        except Exception:
            pass
    yield


app = FastAPI(
    title="NeuroCortex API",
    version="1.0.0",
    description="NeuroCortex longitudinal research platform backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    **cors_middleware_options(settings),
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
app.include_router(golden_vault.router, prefix=settings.api_prefix)
app.include_router(golden_vault_dashboard.router, prefix=settings.api_prefix)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.researcher import ResearcherLoginRequest, ResearcherLoginResponse
from app.services.researcher_auth_service import ResearcherAuthError, login_researcher_with_invite

router = APIRouter(prefix="/auth/researcher", tags=["auth"])


@router.post("/login", response_model=ResearcherLoginResponse)
def login_researcher(
    payload: ResearcherLoginRequest,
    db: Session = Depends(get_db),
) -> ResearcherLoginResponse:
    try:
        return login_researcher_with_invite(db, payload.invite_code)
    except ResearcherAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Researcher login failed",
        ) from exc

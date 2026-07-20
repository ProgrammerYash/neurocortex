from fastapi import APIRouter, HTTPException

from app.schemas.consent import CurrentConsentResponse
from app.services.consent_content import ConsentTemplateError, current_consent_content

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/current", response_model=CurrentConsentResponse)
def get_current_consent() -> CurrentConsentResponse:
    try:
        return CurrentConsentResponse(**current_consent_content())
    except ConsentTemplateError as exc:
        raise HTTPException(status_code=503, detail="Current consent form is unavailable") from exc

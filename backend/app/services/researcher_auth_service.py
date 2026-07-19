from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.researcher import Researcher
from app.models.researcher_invite import ResearcherInvite
from app.schemas.researcher import ResearcherLoginResponse
from app.utils.security import create_researcher_access_token, verify_invite_code


class ResearcherAuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def login_researcher_with_invite(db: Session, invite_code: str) -> ResearcherLoginResponse:
    invites = db.execute(
        select(ResearcherInvite)
        .options(selectinload(ResearcherInvite.researcher))
    ).scalars().all()

    matched_invite: ResearcherInvite | None = None
    for invite in invites:
        if verify_invite_code(invite_code, invite.code_hash):
            matched_invite = invite
            break

    if matched_invite is None:
        raise ResearcherAuthError("Invalid researcher invite code", status_code=401)

    now = datetime.now(UTC)
    if matched_invite.expires_at is not None and matched_invite.expires_at <= now:
        raise ResearcherAuthError("Researcher invite code has expired", status_code=401)

    researcher = matched_invite.researcher
    if researcher is None:
        raise ResearcherAuthError("Researcher account not found", status_code=401)

    matched_invite.used_at = now
    db.commit()

    token = create_researcher_access_token(
        researcher_id=researcher.id,
        display_name=researcher.display_name,
    )
    return ResearcherLoginResponse(
        access_token=token,
        researcher_id=str(researcher.id),
        display_name=researcher.display_name,
    )

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.models.participant_game_data import ParticipantGameData
from app.schemas.game import GameDataPayload


class GameDataError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_participant_game_data(db: Session, participant: Participant) -> dict | None:
    row = db.execute(
        select(ParticipantGameData).where(ParticipantGameData.participant_id == participant.id)
    ).scalar_one_or_none()
    if row is None:
        return None
    return row.game_data


def upsert_participant_game_data(
    db: Session,
    participant: Participant,
    game_data: dict,
) -> dict:
    try:
        validated = GameDataPayload.model_validate(game_data)
    except Exception as exc:
        raise GameDataError("Invalid game data payload", status_code=400) from exc

    payload = validated.model_dump()
    now = datetime.now(UTC)
    row = db.execute(
        select(ParticipantGameData).where(ParticipantGameData.participant_id == participant.id)
    ).scalar_one_or_none()

    if row is None:
        row = ParticipantGameData(
            participant_id=participant.id,
            game_data=payload,
            updated_at=now,
        )
        db.add(row)
    else:
        row.game_data = payload
        row.updated_at = now

    db.commit()
    db.refresh(row)
    return row.game_data

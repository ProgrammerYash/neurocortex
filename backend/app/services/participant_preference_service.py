from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.services.participant_account_service import AccountError, assert_participant_access
from app.services.study_frequency import validate_study_frequency


class ParticipantPreferenceError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def update_study_frequency(
    db: Session,
    participant: Participant,
    *,
    study_frequency: str,
    token_auth_version: int | None,
) -> Participant:
    try:
        assert_participant_access(
            participant,
            token_auth_version=token_auth_version,
            allow_pin_change_only=False,
        )
    except AccountError as exc:
        raise ParticipantPreferenceError(exc.message, status_code=exc.status_code) from exc

    try:
        validated = validate_study_frequency(study_frequency)
    except ValueError as exc:
        raise ParticipantPreferenceError(str(exc), status_code=422) from exc

    participant.study_frequency = validated
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant

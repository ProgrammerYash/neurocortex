from pydantic import BaseModel, ConfigDict


class ResearchParticipantRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    role: str = "participant"
    grade: str
    ageRange: str
    petChoice: str
    joinedDate: str
    joinedAt: int


class ResearchStatsResponse(BaseModel):
    total_participants: int
    total_sessions: int
    completion_rate: float
    average_module_completion: float

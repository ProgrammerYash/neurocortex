from datetime import datetime

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


class DashboardSummaryResponse(BaseModel):
    totalParticipants: int
    totalSessions: int
    activeParticipants7d: int
    averageSessionCompletion: float | None = None
    averageReactionTimeMs: float | None = None
    averageStress: float | None = None
    averageFatigue: float | None = None
    averageSleepHours: float | None = None
    averageMemoryAccuracy: float | None = None
    participantFeedbackEnabled: bool = False
    participantFeedbackUpdatedAt: datetime | None = None
    modelConfigured: bool = False
    modelVersion: str | None = None


class DashboardParticipantRow(BaseModel):
    participantId: str
    studentName: str | None = None
    guardianName: str | None = None
    grade: str
    ageRange: str
    ageDisplay: str
    joinedAt: datetime
    joinedDisplay: str
    sessions: int
    lastActiveAt: datetime | None = None
    lastActiveDisplay: str | None = None
    status: str
    averageReactionTimeMs: float | None = None
    averageStress: float | None = None
    averageFatigue: float | None = None
    averageSleepHours: float | None = None
    averageMemoryAccuracy: float | None = None
    sessionCompletion: float | None = None
    consentRecorded: bool = False
    consentRecordId: str | None = None
    studyFrequency: str | None = None
    studyFrequencyLabel: str = "Not Selected"


class DashboardParticipantsPage(BaseModel):
    items: list[DashboardParticipantRow]
    total: int
    limit: int
    offset: int


class DashboardSessionHistoryRow(BaseModel):
    date: str
    reactionCompleted: bool
    typingCompleted: bool
    memoryCompleted: bool
    attentionCompleted: bool
    surveyCompleted: bool
    complete: bool


class DashboardParticipantDetail(BaseModel):
    participantId: str
    studentName: str | None = None
    guardianName: str | None = None
    grade: str
    ageRange: str
    ageDisplay: str
    joinedAt: datetime
    joinedDisplay: str
    status: str
    sessionsStarted: int
    sessionsCompleted: int
    sessionCompletion: float | None = None
    lastActiveAt: datetime | None = None
    lastActiveDisplay: str | None = None
    averageReactionTimeMs: float | None = None
    averageStress: float | None = None
    averageFatigue: float | None = None
    averageSleepHours: float | None = None
    averageMemoryAccuracy: float | None = None
    recentSessions: list[DashboardSessionHistoryRow]
    isSuspended: bool = False
    suspendedAt: datetime | None = None
    suspendedUntil: datetime | None = None
    suspensionReason: str | None = None
    suspendedUntilDisplay: str | None = None
    isDisabled: bool = False
    disabledAt: datetime | None = None
    disabledReason: str | None = None
    isRemoved: bool = False
    removedAt: datetime | None = None
    removalReason: str | None = None
    mustChangePin: bool = False
    consentRecorded: bool = False
    consentRecordId: str | None = None
    consentVersion: str | None = None
    consentStudentSignedDisplay: str | None = None
    consentGuardianSignedDisplay: str | None = None
    studyFrequency: str | None = None
    studyFrequencyLabel: str = "Not Selected"

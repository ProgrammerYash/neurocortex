"""Versioned consent wording and survey snapshot derived from the approved PDF/UI."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

CONSENT_VERSION = "neurocortex-consent-v1"
SURVEY_VERSION = "daily-survey-v1"
EXPECTED_TEMPLATE_SHA256 = "c0431445efd312f6975762aa9a2e48d06f9c991a545c978c718b8bc951eb1c95"
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "consent"
    / "neurocortex-informed-consent-v1.pdf"
)

STATIC_FIELD_MAP = {
    "student_researcher": "Form 4 Student Researchers",
    "project_title": "Form 4 IC Title of Project",
    "purpose": "Form 4 Purpose of the Project",
    "participation_activities": "Form 4 Participation Asks",
    "time_required": "Form 4 Time Required",
    "potential_risks": "Form 4 Potential Risks of Study",
    "potential_benefits": "Form 4 Benefits",
    "confidentiality": "Form 4 Confidentiality Maintained",
    "questions_contact": "Form 4 Questions Contact",
    "adult_sponsor": "Form 4 Adult Sponsor Name",
    "adult_sponsor_contact": "Form 4 Adult Sponsor Phone/Email",
}

EXPECTED_STATIC_VALUES = {
    "student_researcher": "Yash Gupta",
    "project_title": (
        "NeuroCortex - Predictive Model Designed to Predict Burnout and "
        "Cognitive Stress Overload"
    ),
    "purpose": "Collect data from students daily through digital biomakers to train an AI predicitve model",
    "participation_activities": "Log in to the app daily for 3 months and complete daily tasks",
    "time_required": "10 Minutes daily",
    "potential_risks": "N/A",
    "potential_benefits": "N/A",
    "confidentiality": "Names of all users are confidential and each user is given an anonymous ID",
    "questions_contact": "+1 (551) 257 - 9190",
    "adult_sponsor": "Ms. Jennifer Donnelly",
    "adult_sponsor_contact": "jdonnelly@ucboe.us",
}

VOLUNTARY_PARTICIPATION = (
    "Participation in this study is completely voluntary. If you decide not to "
    "participate there will not be negative consequences."
)
MAY_STOP = (
    "Please be aware that if you decide to participate, you may stop "
    "participating at any time"
)
MAY_SKIP_QUESTIONS = "and you may decide not to answer any specific question."
SIGNING_EXPLANATION = (
    "By signing this form I am attesting that I have read and understand the "
    "information above and I freely give my consent/assent to participate or "
    "permission for my child to participate."
)
PARTICIPANT_ACKNOWLEDGMENT = (
    "I have read and understand the study information. I understand that "
    "participation is voluntary, and I agree to participate."
)
GUARDIAN_ACKNOWLEDGMENT = (
    "I certify that I am this participant's parent or legal guardian. I have "
    "read and understand the study information, and I give permission for my "
    "child to participate."
)

# Exact snapshot of participant-visible controls in DailySurvey.jsx at consent v1.
DAILY_SURVEY_SNAPSHOT = (
    {
        "question": "Stress Level",
        "instructions": "1=very low, 10=very high",
        "response": "Whole-number scale: 1 through 10",
    },
    {
        "question": "Fatigue",
        "instructions": "1=energetic, 10=exhausted",
        "response": "Whole-number scale: 1 through 10",
    },
    {
        "question": "Motivation",
        "instructions": "1=very low, 10=very high",
        "response": "Whole-number scale: 1 through 10",
    },
    {
        "question": "Mood",
        "instructions": "1=very poor, 10=excellent",
        "response": "Whole-number scale: 1 through 10",
    },
    {
        "question": "Social Stress",
        "instructions": "1=none, 10=very high",
        "response": "Whole-number scale: 1 through 10",
    },
    {
        "question": "Sleep (hrs)",
        "instructions": "Enter hours slept.",
        "response": "Number from 0 through 12",
    },
    {
        "question": "Study (hrs)",
        "instructions": "Enter hours spent studying.",
        "response": "Number from 0 through 16",
    },
    {
        "question": "HW (hrs)",
        "instructions": "Enter hours spent on homework.",
        "response": "Number from 0 through 12",
    },
    {
        "question": "Major exam in the next 3 days?",
        "instructions": "Select one answer.",
        "response": "Yes; No",
    },
)


class ConsentTemplateError(RuntimeError):
    pass


def template_sha256() -> str:
    try:
        digest = hashlib.sha256(TEMPLATE_PATH.read_bytes()).hexdigest()
    except OSError as exc:
        raise ConsentTemplateError("Approved consent template is unavailable") from exc
    if digest != EXPECTED_TEMPLATE_SHA256:
        raise ConsentTemplateError("Approved consent template hash does not match configured version")
    return digest


@lru_cache(maxsize=1)
def current_consent_content() -> dict[str, str]:
    template_sha256()
    try:
        fields = PdfReader(str(TEMPLATE_PATH)).get_fields() or {}
    except Exception as exc:
        raise ConsentTemplateError("Approved consent template cannot be read") from exc

    missing = [field for field in STATIC_FIELD_MAP.values() if field not in fields]
    if missing:
        raise ConsentTemplateError("Approved consent template is missing required fields")

    extracted: dict[str, str] = {}
    for key, field_name in STATIC_FIELD_MAP.items():
        value = fields[field_name].get("/V")
        extracted[key] = str(value or "").strip()
    if extracted != EXPECTED_STATIC_VALUES:
        raise ConsentTemplateError("Approved consent template values do not match configured version")

    return {
        "consent_version": CONSENT_VERSION,
        "survey_version": SURVEY_VERSION,
        "template_sha256": EXPECTED_TEMPLATE_SHA256,
        **extracted,
        "voluntary_participation": VOLUNTARY_PARTICIPATION,
        "may_stop": MAY_STOP,
        "may_skip_questions": MAY_SKIP_QUESTIONS,
        "signing_explanation": SIGNING_EXPLANATION,
        "participant_acknowledgment": PARTICIPANT_ACKNOWLEDGMENT,
        "guardian_acknowledgment": GUARDIAN_ACKNOWLEDGMENT,
    }

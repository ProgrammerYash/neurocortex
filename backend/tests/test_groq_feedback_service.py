from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.groq_feedback_service import (
    GROQ_FEEDBACK_RESPONSE_FORMAT,
    GroqFeedbackError,
    GroqFeedbackModel,
    generate_groq_feedback,
)


def test_no_completed_sessions_skips_provider_call():
    with patch("groq.Groq") as groq_cls:
        model, request_id = generate_groq_feedback({"completed_session_count": 0})
    groq_cls.assert_not_called()
    assert model.status == "insufficient_data"
    assert request_id is None


def test_missing_api_key_reports_not_configured():
    with patch("app.services.groq_feedback_service.get_settings") as settings:
        settings.return_value.groq_api_key = ""
        settings.return_value.groq_model = "llama"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 0
        with pytest.raises(GroqFeedbackError) as exc:
            generate_groq_feedback({"completed_session_count": 3, "metrics": {}})
    assert exc.value.code == "NOT_CONFIGURED"


def test_valid_json_accepted():
    payload = {
        "status": "available",
        "level": "low",
        "headline": "Lower strain indicators",
        "summary": "Your recent study results show fewer indicators associated with cognitive strain.",
        "factors": ["Reaction-time consistency"],
    }
    mock_response = MagicMock()
    mock_response.id = "req-abc"
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]

    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 0
        groq_cls.return_value.chat.completions.create.return_value = mock_response
        model, request_id = generate_groq_feedback({"completed_session_count": 2, "metrics": {"rt_mean_ms": 420}})

    assert isinstance(model, GroqFeedbackModel)
    assert model.level == "low"
    assert request_id == "req-abc"


def test_extra_properties_rejected():
    payload = {
        "status": "available",
        "level": "low",
        "headline": "Lower strain indicators",
        "summary": "Summary text here.",
        "factors": [],
        "unexpected": True,
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]

    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 0
        groq_cls.return_value.chat.completions.create.return_value = mock_response
        with pytest.raises(GroqFeedbackError) as exc:
            generate_groq_feedback({"completed_session_count": 1})
    assert exc.value.code == "SCHEMA_MISMATCH"


def test_groq_request_uses_strict_json_schema():
    captured = {}

    def capture_create(**kwargs):
        captured.update(kwargs)
        mock_response = MagicMock()
        mock_response.id = "req-schema"
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "status": "available",
                            "level": "low",
                            "headline": "Lower strain indicators",
                            "summary": "Summary within limit.",
                            "factors": ["Reaction-time consistency"],
                        }
                    )
                )
            )
        ]
        return mock_response

    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 0
        groq_cls.return_value.chat.completions.create.side_effect = capture_create
        generate_groq_feedback({"completed_session_count": 2})

    response_format = captured["response_format"]
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert schema["properties"]["status"]["enum"] == ["available", "insufficient_data"]
    assert schema["properties"]["level"]["enum"] == ["low", "moderate", "elevated", "unclear"]
    assert schema["properties"]["headline"]["maxLength"] == 80
    assert schema["properties"]["factors"]["maxItems"] == 3
    assert captured.get("stream") is False
    assert response_format == GROQ_FEEDBACK_RESPONSE_FORMAT


def test_metrics_payload_excludes_pii_in_user_message():
    captured = {}

    def capture_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        mock_response = MagicMock()
        mock_response.id = "req-1"
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "status": "available",
                            "level": "moderate",
                            "headline": "Moderate strain indicators",
                            "summary": "Neutral summary for testing.",
                            "factors": [],
                        }
                    )
                )
            )
        ]
        return mock_response

    metrics = {
        "completed_session_count": 2,
        "reaction_time_ms_mean": 450,
    }
    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 0
        groq_cls.return_value.chat.completions.create.side_effect = capture_create
        generate_groq_feedback(metrics)

    user_content = captured["messages"][1]["content"]
    assert "NC-" not in user_content
    assert "@" not in user_content
    assert "guardian" not in user_content.lower()

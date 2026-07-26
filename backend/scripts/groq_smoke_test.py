"""Optional Groq smoke test — run manually when GROQ_API_KEY and GROQ_MODEL are set."""

from __future__ import annotations

import json
import sys

from app.services.groq_feedback_service import GroqFeedbackError, GroqFeedbackModel, generate_groq_feedback


def main() -> int:
    synthetic = {
        "completed_session_count": 3,
        "reaction_time_ms_mean": 412.5,
        "reaction_time_ms_std": 48.2,
        "typing_wpm_mean": 42.0,
        "memory_accuracy_mean": 0.71,
        "stroop_accuracy_mean": 0.88,
        "survey_stress_mean": 2.4,
    }
    try:
        model, request_id = generate_groq_feedback(synthetic)
    except GroqFeedbackError as exc:
        print("Smoke test failed.")
        print(f"error_code: {exc.code}")
        print(f"http_status: {exc.status_code}")
        print(f"message: {exc.message}")
        return 1
    except Exception as exc:
        print("Smoke test failed.")
        print(f"error_code: UNEXPECTED_ERROR")
        print("http_status: 500")
        print(f"message: {exc.__class__.__name__}: unexpected failure")
        return 1
    GroqFeedbackModel.model_validate(model.model_dump())
    print("Smoke test passed.")
    print(json.dumps({"status": model.status, "level": model.level, "request_id": request_id}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

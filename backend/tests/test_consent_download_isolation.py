"""Regression: consent download-all empty only when no consent rows exist in isolated DB."""

from __future__ import annotations

import io
import zipfile

from app.models.researcher import Researcher
from app.utils.security import create_researcher_access_token


def test_download_all_empty_when_no_consent_rows(client, db):
    researcher = Researcher(display_name="Empty Archive Tester", email="empty-archive@example.test")
    db.add(researcher)
    db.flush()
    headers = {
        "Authorization": "Bearer "
        + create_researcher_access_token(
            researcher_id=researcher.id,
            display_name=researcher.display_name,
        )
    }
    response = client.get("/v1/researcher/consents/download-all", headers=headers)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["manifest.csv"]

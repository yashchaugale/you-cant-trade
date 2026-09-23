from fastapi.testclient import TestClient

import server
from database.local_database import (
    create_memory_finding,
    initialise,
)


def test_memory_api_lists_findings(monkeypatch):
    initialise()

    finding = create_memory_finding(
        {
            "id": "memory-api-1",
            "type": "EDGE",
            "statement": "API test edge finding",
            "sampleSize": 4,
            "evidenceStrength": "LIMITED",
            "firstObserved": "2026-01-01T10:00:00Z",
            "lastVerified": None,
            "status": "OBSERVED",
            "supportingTradeIds": [],
            "contractVersion": 1,
        }
    )

    response = TestClient(server.app).get("/memory")

    assert response.status_code == 200

    payload = response.json()

    assert payload["version"] == 1
    assert any(item["id"] == finding["id"] for item in payload["findings"])


def test_memory_api_filters_findings():
    response = TestClient(server.app).get(
        "/memory",
        params={"status": "OBSERVED", "finding_type": "EDGE"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert all(item["status"] == "OBSERVED" for item in payload["findings"])
    assert all(item["type"] == "EDGE" for item in payload["findings"])


def test_memory_api_rejects_invalid_filters():
    response = TestClient(server.app).get(
        "/memory",
        params={"status": "INVALID"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported Memory status: INVALID"


def test_memory_api_returns_finding_with_verification_history():
    finding = create_memory_finding(
        {
            "id": "memory-api-detail-1",
            "type": "SETUP",
            "statement": "API detail test finding",
            "sampleSize": 3,
            "evidenceStrength": "LIMITED",
            "firstObserved": "2026-01-02T10:00:00Z",
            "lastVerified": None,
            "status": "OBSERVED",
            "supportingTradeIds": [],
            "contractVersion": 1,
        }
    )

    response = TestClient(server.app).get(
        f"/memory/{finding['id']}",
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["version"] == 1
    assert payload["finding"]["id"] == finding["id"]
    assert payload["finding"]["statement"] == "API detail test finding"
    assert payload["verificationHistory"] == []


def test_memory_api_returns_404_for_missing_finding():
    response = TestClient(server.app).get(
        "/memory/does-not-exist",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory finding not found"

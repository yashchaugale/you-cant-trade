from fastapi.testclient import TestClient

import server
from database.local_database import (
    connect,
    create_memory_finding,
    initialise,
)

import pytest


@pytest.fixture(autouse=True)
def clean_memory_api_records():
    initialise()

    with connect() as connection:
        connection.execute(
            "delete from memory_verifications "
            "where id like 'verification-api-%'"
        )
        connection.execute(
            "delete from memory_findings "
            "where id like 'memory-api-%'"
        )

    yield

    with connect() as connection:
        connection.execute(
            "delete from memory_verifications "
            "where id like 'verification-api-%'"
        )
        connection.execute(
            "delete from memory_findings "
            "where id like 'memory-api-%'"
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


def test_memory_api_creates_finding():
    response = TestClient(server.app).post(
        "/memory",
        json={
            "id": "memory-api-write-1",
            "type": "EDGE",
            "statement": "Created through the API",
            "sampleSize": 3,
            "evidenceStrength": "LIMITED",
            "firstObserved": "2026-02-01T10:00:00Z",
            "status": "OBSERVED",
            "supportingTradeIds": [],
            "contractVersion": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["version"] == 1
    assert payload["finding"]["id"] == "memory-api-write-1"
    assert payload["finding"]["statement"] == "Created through the API"



def _create_write_test_finding():
    response = TestClient(server.app).post(
        "/memory",
        json={
            "id": "memory-api-write-1",
            "type": "EDGE",
            "statement": "Created through the API",
            "sampleSize": 3,
            "evidenceStrength": "LIMITED",
            "firstObserved": "2026-02-01T10:00:00Z",
            "status": "OBSERVED",
            "supportingTradeIds": [],
            "contractVersion": 1,
        },
    )
    assert response.status_code == 200


def test_memory_api_challenges_finding():
    _create_write_test_finding()
    response = TestClient(server.app).post(
        "/memory/memory-api-write-1/challenge",
    )

    assert response.status_code == 200
    assert response.json()["finding"]["status"] == "CHALLENGED"


def test_memory_api_updates_finding():
    _create_write_test_finding()
    response = TestClient(server.app).patch(
        "/memory/memory-api-write-1",
        json={"statement": "Updated through the API"},
    )

    assert response.status_code == 200
    assert response.json()["finding"]["statement"] == "Updated through the API"
    assert response.json()["finding"]["status"] == "OBSERVED"


def test_memory_api_rechecks_finding():
    _create_write_test_finding()
    response = TestClient(server.app).post(
        "/memory/memory-api-write-1/recheck",
        json={
            "id": "verification-api-1",
            "verifiedAt": "2026-02-15T10:00:00Z",
            "status": "ACTIVE",
            "sampleSize": 5,
            "evidenceStrength": "MODERATE",
            "supportingTradeIds": [],
            "contractVersion": 1,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["finding"]["status"] == "ACTIVE"
    assert payload["finding"]["lastVerified"] == "2026-02-15T10:00:00Z"
    assert payload["verification"]["id"] == "verification-api-1"


def test_memory_api_retires_finding():
    _create_write_test_finding()
    response = TestClient(server.app).post(
        "/memory/memory-api-write-1/retire",
    )

    assert response.status_code == 200
    assert response.json()["finding"]["status"] == "RETIRED"


def test_memory_api_write_returns_404_for_missing_finding():
    response = TestClient(server.app).post(
        "/memory/does-not-exist/challenge",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory finding not found"

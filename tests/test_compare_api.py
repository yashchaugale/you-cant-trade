from fastapi.testclient import TestClient

import server


def _trade(trade_id, day, result="WIN", actual_r=None):
    trade = {
        "id": trade_id,
        "timestamp": f"2026-01-{day:02d}T10:00:00Z",
        "result": result,
        "direction": "LONG",
    }

    if actual_r is not None:
        trade["intelligence"] = {
            "calculated": {
                "features": {
                    "actualR": actual_r,
                }
            }
        }

    return trade


class FakeProvider:
    def __init__(self, trades):
        self.trades = trades

    def historical_candidate_limit(self):
        return 100

    def list_trades(self, limit=None):
        return self.trades[:limit]


def test_compare_api_returns_deterministic_comparison(monkeypatch):
    trades = [
        _trade("1", 1, result="LOSS", actual_r=-1.0),
        _trade("2", 2, result="WIN", actual_r=1.0),
        _trade("3", 3, result="WIN", actual_r=2.0),
        _trade("4", 4, result="LOSS", actual_r=-0.5),
    ]

    monkeypatch.setattr(
        server,
        "get_storage_provider",
        lambda: FakeProvider(trades),
    )

    response = TestClient(server.app).get(
        "/compare",
        params={"current_count": 2, "previous_count": 2},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["version"] == 1
    assert payload["periods"]["previous"]["tradeIds"] == ["1", "2"]
    assert payload["periods"]["current"]["tradeIds"] == ["3", "4"]

    assert payload["performance"]["winRate"]["previous"] == 0.5
    assert payload["performance"]["winRate"]["current"] == 0.5

    assert payload["performance"]["averageR"]["previous"] == 0.0
    assert payload["performance"]["averageR"]["current"] == 0.75


def test_compare_api_rejects_invalid_period_sizes():
    response = TestClient(server.app).get(
        "/compare",
        params={"current_count": 0, "previous_count": 2},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Compare period sizes must be positive"

from datetime import datetime, timedelta, timezone

from services.compare import compare_periods
from services.current_understanding import build_current_understanding
from services.leak_map import build_leak_map
from services.pattern_discovery import discover_patterns


def make_trade(
    trade_id: str,
    timestamp: datetime,
    *,
    setup: str,
    session: str,
    direction: str = "LONG",
    result: str = "WIN",
    actual_r: float | None = None,
    execution_tag: str | None = None,
) -> dict:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    trade = {
        "id": trade_id,
        "timestamp": timestamp.isoformat(),
        "setup": setup,
        "session": session,
        "direction": direction,
        "result": result,
    }

    if actual_r is not None:
        trade["intelligence"] = {
            "calculated": {
                "features": {
                    "actualR": actual_r,
                }
            }
        }

    if execution_tag is not None:
        trade["executionTag"] = execution_tag

        # Always use LONG here so the requested R value maps directly
        # to the exit price.
        trade["direction"] = "LONG"
        trade["entry"] = 100.0
        trade["stopLoss"] = 99.0
        trade["exitPrice"] = 100.0 + actual_r

    return trade


def baseline_trades() -> list[dict]:
    """
    Baseline journal:
    - 4 Sunday trades
    - every other categorical dimension is deliberately unique
    - Sunday is therefore the only meaningful recurring pattern
    """
    sunday_dates = [
        datetime(2026, 1, 4, 1),
        datetime(2026, 1, 18, 3),
        datetime(2026, 2, 1, 5),
        datetime(2026, 2, 15, 7),
    ]

    trades = []

    for index, timestamp in enumerate(sunday_dates, start=1):
        trades.append(
            make_trade(
                f"base-{index}",
                timestamp,
                setup=f"Baseline-{index}",
                session=f"BaselineSession-{index}",
                direction=f"BaselineDirection-{index}",
                result="WIN" if index == 1 else "LOSS",
            )
        )

    weekday_dates = [
        datetime(2026, 1, 5, 1),  # Monday
        datetime(2026, 1, 6, 3),  # Tuesday
        datetime(2026, 1, 7, 5),  # Wednesday
    ]

    for index, timestamp in enumerate(weekday_dates, start=5):
        trades.append(
            make_trade(
                f"base-{index}",
                timestamp,
                setup=f"Baseline-{index}",
                session=f"BaselineSession-{index}",
                direction=f"BaselineDirection-{index}",
                result="WIN" if index % 2 else "LOSS",
            )
        )

    return trades


def sunday_trades_with_actual_r(
    start_id: int = 200,
    positive: bool = True,
) -> list[dict]:
    """Ten additional Sunday trades with measured R."""
    dates = [
        datetime(2026, 3, 1, 1),
        datetime(2026, 3, 15, 3),
        datetime(2026, 3, 29, 5),
        datetime(2026, 4, 12, 7),
        datetime(2026, 4, 26, 9),
        datetime(2026, 5, 10, 11),
        datetime(2026, 5, 24, 13),
        datetime(2026, 6, 7, 15),
        datetime(2026, 6, 21, 17),
        datetime(2026, 7, 5, 19),
    ]

    value = 0.5 if positive else -0.5

    return [
        make_trade(
            f"sunday-{start_id + index}",
            timestamp,
            setup=f"SundaySetup-{start_id + index}",
            session=f"SundaySession-{start_id + index}",
            direction=f"SundayDirection-{start_id + index}",
            result="WIN" if positive else "LOSS",
            actual_r=value,
        )
        for index, timestamp in enumerate(dates)
    ]


def breakout_trades(start_id: int = 100) -> list[dict]:
    """Ten breakout trades spread across three months."""
    dates = [
        datetime(2026, 1, 6, 1),
        datetime(2026, 1, 13, 3),
        datetime(2026, 1, 27, 5),
        datetime(2026, 2, 3, 7),
        datetime(2026, 2, 10, 9),
        datetime(2026, 2, 24, 11),
        datetime(2026, 3, 3, 13),
        datetime(2026, 3, 10, 15),
        datetime(2026, 3, 24, 17),
        datetime(2026, 3, 31, 19),
    ]

    return [
        make_trade(
            f"breakout-{start_id + index}",
            timestamp,
            setup="Breakout",
            session=f"BreakoutSession-{index}",
            direction=f"BreakoutDirection-{index}",
            result="WIN",
            actual_r=0.6,
        )
        for index, timestamp in enumerate(dates)
    ]


def late_entry_leaks(start_id: int = 300) -> list[dict]:
    """Ten measured negative late-entry occurrences."""
    dates = [
        datetime(2026, 1, 7, 1),
        datetime(2026, 1, 14, 3),
        datetime(2026, 1, 21, 5),
        datetime(2026, 1, 28, 7),
        datetime(2026, 2, 4, 9),
        datetime(2026, 2, 11, 11),
        datetime(2026, 2, 18, 13),
        datetime(2026, 2, 25, 15),
        datetime(2026, 3, 4, 17),
        datetime(2026, 3, 11, 19),
    ]

    return [
        make_trade(
            f"late-{start_id + index}",
            timestamp,
            setup=f"LateSetup-{index}",
            session=f"LateSession-{index}",
            result="LOSS",
            actual_r=-0.4,
            execution_tag="LATE_ENTRY",
        )
        for index, timestamp in enumerate(dates)
    ]


def current_understanding_for(trades: list[dict]) -> dict:
    patterns = discover_patterns(trades)
    leaks = build_leak_map(trades)
    compare = compare_periods(
        trades,
        current_count=min(10, len(trades)),
        previous_count=min(10, len(trades)),
    )

    return build_current_understanding(
        trade_count=len(trades),
        patterns=patterns,
        leaks=leaks,
        compare=compare,
    )


def test_baseline_home_understanding():
    payload = current_understanding_for(baseline_trades())

    assert payload["status"] == "READY"
    assert payload["observation"] is not None
    assert payload["observation"]["source"]["dimension"] == "day"
    assert payload["observation"]["source"]["value"] == "Sunday"
    assert "Sunday" in payload["observation"]["statement"]


def test_new_stronger_pattern_can_change_home():
    trades = baseline_trades() + breakout_trades()

    payload = current_understanding_for(trades)

    assert payload["status"] == "READY"
    assert payload["observation"] is not None
    assert payload["observation"]["source"]["dimension"] == "setup"
    assert payload["observation"]["source"]["value"] == "Breakout"
    assert payload["observation"]["sampleSize"] == 10
    assert "+0.60R" in payload["observation"]["statement"]


def test_existing_pattern_updates_when_new_evidence_is_added():
    trades = baseline_trades() + sunday_trades_with_actual_r()

    payload = current_understanding_for(trades)

    assert payload["observation"] is not None
    assert payload["observation"]["source"]["dimension"] == "day"
    assert payload["observation"]["source"]["value"] == "Sunday"
    assert payload["observation"]["sampleSize"] == 14
    assert "+0.50R" in payload["observation"]["statement"]


def test_deteriorating_pattern_changes_the_understanding():
    trades = baseline_trades() + sunday_trades_with_actual_r(positive=False)

    payload = current_understanding_for(trades)

    assert payload["observation"] is not None
    assert payload["observation"]["source"]["value"] == "Sunday"
    assert "-0.50R" in payload["observation"]["statement"]
    assert "wrong reason" in payload["observation"]["statement"]


def test_home_can_surface_a_pattern_and_a_measured_leak():
    trades = baseline_trades() + breakout_trades() + late_entry_leaks()

    payload = current_understanding_for(trades)

    assert payload["observation"] is not None
    assert payload["observation"]["source"]["value"] == "Breakout"

    assert payload["watch"] is not None
    assert payload["watch"]["type"] == "LEAK"
    assert "Late entries" in payload["watch"]["statement"]
    assert "-4.00R" in payload["watch"]["statement"]


def test_home_avoids_claiming_a_pattern_with_too_little_evidence():
    trades = baseline_trades()[:2]

    payload = current_understanding_for(trades)

    assert payload["status"] == "LEARNING"
    assert payload["observation"] is None


def test_home_reports_a_real_recent_change_when_periods_exist():
    trades = []

    for index in range(10):
        trades.append(
            make_trade(
                f"compare-{index}",
                datetime(2026, 1, 1) + timedelta(days=index),
                setup=f"CompareSetup-{index}",
                session=f"CompareSession-{index}",
                result="WIN" if index >= 5 else "LOSS",
                actual_r=0.8 if index >= 5 else -0.2,
            )
        )

    patterns = discover_patterns(trades)
    leaks = build_leak_map(trades)
    compare = compare_periods(
        trades,
        current_count=5,
        previous_count=5,
    )

    payload = build_current_understanding(
        trade_count=len(trades),
        patterns=patterns,
        leaks=leaks,
        compare=compare,
    )

    assert payload["recentChange"] is not None
    assert "latest 5 trades" in payload["recentChange"]["statement"]
    assert "+0.80R" in payload["recentChange"]["statement"]
    assert "-0.20R" in payload["recentChange"]["statement"]

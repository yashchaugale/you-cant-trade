"""Provider-neutral deterministic analytics for You Can't Trade."""

from __future__ import annotations

from typing import Any


def calculate_journal_analytics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate journal analytics from canonical trades without storage or AI."""
    reviewed = [
        trade
        for trade in trades
        if trade.get("result") in {"WIN", "LOSS", "BE"}
    ]

    def counts(values: list[Any]) -> list[dict[str, Any]]:
        tally: dict[str, int] = {}
        for value in values:
            if isinstance(value, str) and value.strip():
                key = value.strip()
                tally[key] = tally.get(key, 0) + 1
        return [
            {"value": value, "count": count}
            for value, count in sorted(
                tally.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    planned_r: list[float] = []
    actual_r: list[float] = []

    for trade in trades:
        entry = trade.get("entry")
        stop = trade.get("stopLoss")
        take_profit = trade.get("takeProfit")

        if all(
            isinstance(value, (int, float))
            for value in (entry, stop, take_profit)
        ):
            risk = abs(entry - stop)

            if risk > 0:
                planned_r.append(abs(take_profit - entry) / risk)

    for trade in reviewed:
        entry = trade.get("entry")
        stop = trade.get("stopLoss")
        exit_price = trade.get("exitPrice")
        direction = trade.get("direction")

        if not all(
            isinstance(value, (int, float))
            for value in (entry, stop, exit_price)
        ):
            continue

        if direction not in {"LONG", "SHORT"}:
            continue

        risk = abs(entry - stop)
        if risk == 0:
            continue

        profit = (
            exit_price - entry
            if direction == "LONG"
            else entry - exit_price
        )
        actual_r.append(profit / risk)

    wins = sum(trade.get("result") == "WIN" for trade in reviewed)
    losses = sum(trade.get("result") == "LOSS" for trade in reviewed)
    break_even = sum(trade.get("result") == "BE" for trade in reviewed)
    decided_trades = wins + losses

    return {
        "totalTrades": len(trades),
        "reviewedTrades": len(reviewed),
        "winRate": (
            round(wins / decided_trades, 6)
            if decided_trades
            else None
        ),
        "outcomes": {
            "wins": wins,
            "losses": losses,
            "breakEven": break_even,
        },
        "evidence": {
            "outcomeTrades": len(reviewed),
            "plannedRTrades": len(planned_r),
            "actualRTrades": len(actual_r),
        },
        "actualR": {
            "count": len(actual_r),
            "total": round(sum(actual_r), 6),
            "average": (
                round(sum(actual_r) / len(actual_r), 6)
                if actual_r
                else None
            ),
            "median": (
                round(
                    (
                        sorted(actual_r)[len(actual_r) // 2]
                        if len(actual_r) % 2
                        else (
                            sorted(actual_r)[len(actual_r) // 2 - 1]
                            + sorted(actual_r)[len(actual_r) // 2]
                        ) / 2
                    ),
                    6,
                )
                if actual_r
                else None
            ),
        },
        "topSetups": counts([trade.get("setup") for trade in reviewed])[:5],
        "topEmotions": counts(
            [
                emotion
                for trade in reviewed
                for emotion in (trade.get("emotions") or [])
            ]
        )[:5],
        "topExecutionTags": counts(
            [trade.get("executionTag") for trade in reviewed]
        )[:5],
        "sampleWarning": (
            "Capture and review at least 10 trades before treating recurring "
            "patterns as reliable."
            if len(reviewed) < 10
            else None
        ),
    }

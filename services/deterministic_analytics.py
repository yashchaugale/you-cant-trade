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
    actual_r_trades: list[tuple[str, float]] = []

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
        realized_r = profit / risk
        actual_r.append(realized_r)
        actual_r_trades.append((trade.get("result"), realized_r))

    winning_actual_r = [
        realized_r
        for _, realized_r in actual_r_trades
        if realized_r > 0
    ]
    losing_actual_r = [
        realized_r
        for _, realized_r in actual_r_trades
        if realized_r < 0
    ]

    biggest_winner = max(winning_actual_r) if winning_actual_r else None

    gross_profit = sum(
        winning_actual_r
    )
    gross_loss = abs(sum(
        realized_r
        for _, realized_r in actual_r_trades
        if realized_r < 0
    ))

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
        "expectancy": {
            "value": (
                round(sum(actual_r) / len(actual_r), 6)
                if actual_r
                else None
            ),
            "count": len(actual_r_trades),
            "outcomes": {
                "wins": sum(
                    result == "WIN"
                    for result, _ in actual_r_trades
                ),
                "losses": sum(
                    result == "LOSS"
                    for result, _ in actual_r_trades
                ),
                "breakEven": sum(
                    result == "BE"
                    for result, _ in actual_r_trades
                ),
            },
        },
        "profitFactor": {
            "value": (
                round(gross_profit / gross_loss, 6)
                if gross_loss > 0
                else None
            ),
            "count": len(actual_r_trades),
            "grossProfit": round(gross_profit, 6),
            "grossLoss": round(gross_loss, 6),
        },
        "averageWinner": {
            "value": (
                round(sum(winning_actual_r) / len(winning_actual_r), 6)
                if winning_actual_r
                else None
            ),
            "count": len(winning_actual_r),
        },
        "averageLoser": {
            "value": (
                round(sum(losing_actual_r) / len(losing_actual_r), 6)
                if losing_actual_r
                else None
            ),
            "count": len(losing_actual_r),
        },
        "biggestWinner": {
            "value": (
                round(biggest_winner, 6)
                if biggest_winner is not None
                else None
            ),
            "count": len(winning_actual_r),
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

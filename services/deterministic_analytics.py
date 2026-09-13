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

    hourly_counts: dict[int, int] = {}

    for trade in trades:
        timestamp = trade.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            continue

        try:
            from datetime import datetime, timezone
            parsed_timestamp = datetime.fromisoformat(
                timestamp.strip().replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

        hour = parsed_timestamp.astimezone(timezone.utc).hour
        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

    by_hour = [
        {"hour": hour, "count": count}
        for hour, count in sorted(hourly_counts.items())
    ]

    daily_counts: dict[int, int] = {}

    for trade in trades:
        timestamp = trade.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            continue

        try:
            from datetime import datetime, timezone
            parsed_timestamp = datetime.fromisoformat(
                timestamp.strip().replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

        weekday = parsed_timestamp.astimezone(timezone.utc).weekday()
        daily_counts[weekday] = daily_counts.get(weekday, 0) + 1

    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    by_day = [
        {"day": day_names[weekday], "count": daily_counts[weekday]}
        for weekday in range(7)
        if weekday in daily_counts
    ]

    weekly_counts: dict[tuple[int, int], int] = {}

    for trade in trades:
        timestamp = trade.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            continue

        try:
            from datetime import datetime, timezone
            parsed_timestamp = datetime.fromisoformat(
                timestamp.strip().replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

        iso_year, iso_week, _ = parsed_timestamp.astimezone(
            timezone.utc
        ).isocalendar()

        key = (iso_year, iso_week)
        weekly_counts[key] = weekly_counts.get(key, 0) + 1

    by_week = [
        {
            "year": year,
            "week": week,
            "count": count,
        }
        for (year, week), count in sorted(weekly_counts.items())
    ]

    monthly_counts: dict[tuple[int, int], int] = {}

    for trade in trades:
        timestamp = trade.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            continue

        try:
            from datetime import datetime, timezone
            parsed_timestamp = datetime.fromisoformat(
                timestamp.strip().replace("Z", "+00:00")
            )
        except ValueError:
            continue

        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

        utc_timestamp = parsed_timestamp.astimezone(timezone.utc)
        key = (utc_timestamp.year, utc_timestamp.month)
        monthly_counts[key] = monthly_counts.get(key, 0) + 1

    by_month = [
        {
            "year": year,
            "month": month,
            "count": count,
        }
        for (year, month), count in sorted(monthly_counts.items())
    ]

    valid_sessions = {"ASIA", "LONDON", "NEW_YORK", "OTHER"}
    session_counts: dict[str, int] = {}

    for trade in trades:
        session = trade.get("session")
        if session not in valid_sessions:
            continue

        session_counts[session] = session_counts.get(session, 0) + 1

    session_order = ["ASIA", "LONDON", "NEW_YORK", "OTHER"]
    by_session = [
        {"session": session, "count": session_counts[session]}
        for session in session_order
        if session in session_counts
    ]

    setup_sample_counts: dict[str, int] = {}
    setup_wins: dict[str, int] = {}
    setup_losses: dict[str, int] = {}
    setup_actual_r: dict[str, list[float]] = {}
    setup_recent_trades: dict[str, list[dict[str, Any]]] = {}

    for trade in trades:
        setup = trade.get("setup")

        if not isinstance(setup, str) or not setup.strip():
            continue

        setup_name = setup.strip()
        setup_sample_counts[setup_name] = (
            setup_sample_counts.get(setup_name, 0) + 1
        )

        result = trade.get("result")
        if result == "WIN":
            setup_wins[setup_name] = setup_wins.get(setup_name, 0) + 1
        elif result == "LOSS":
            setup_losses[setup_name] = setup_losses.get(setup_name, 0) + 1

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

        setup_actual_r.setdefault(setup_name, []).append(realized_r)

    for setup_name in setup_sample_counts:
        setup_recent_trades[setup_name] = sorted(
            [
                trade
                for trade in trades
                if (
                    isinstance(trade.get("setup"), str)
                    and trade.get("setup").strip() == setup_name
                )
            ],
            key=lambda trade: trade.get("timestamp") or "",
            reverse=True,
        )[:10]

    setup_performance = [
        {
            "setup": setup,
            "sampleSize": count,
            "winRate": (
                round(
                    setup_wins.get(setup, 0)
                    / (
                        setup_wins.get(setup, 0)
                        + setup_losses.get(setup, 0)
                    ),
                    6,
                )
                if (
                    setup_wins.get(setup, 0)
                    + setup_losses.get(setup, 0)
                )
                else None
            ),
            "averageR": (
                round(
                    sum(setup_actual_r[setup])
                    / len(setup_actual_r[setup]),
                    6,
                )
                if setup_actual_r.get(setup)
                else None
            ),
            "expectancy": (
                round(
                    sum(setup_actual_r[setup])
                    / len(setup_actual_r[setup]),
                    6,
                )
                if setup_actual_r.get(setup)
                else None
            ),
            "recentPerformance": (
                lambda recent_trades: {
                    "sampleSize": len(recent_trades),
                    "winRate": (
                        round(
                            sum(
                                trade.get("result") == "WIN"
                                for trade in recent_trades
                            )
                            / (
                                sum(
                                    trade.get("result") == "WIN"
                                    for trade in recent_trades
                                )
                                + sum(
                                    trade.get("result") == "LOSS"
                                    for trade in recent_trades
                                )
                            ),
                            6,
                        )
                        if (
                            sum(
                                trade.get("result") == "WIN"
                                for trade in recent_trades
                            )
                            + sum(
                                trade.get("result") == "LOSS"
                                for trade in recent_trades
                            )
                        )
                        else None
                    ),
                }
            )(setup_recent_trades[setup]),
            "historicalPerformance": {
                "sampleSize": count,
                "winRate": (
                    round(
                        setup_wins.get(setup, 0)
                        / (
                            setup_wins.get(setup, 0)
                            + setup_losses.get(setup, 0)
                        ),
                        6,
                    )
                    if (
                        setup_wins.get(setup, 0)
                        + setup_losses.get(setup, 0)
                    )
                    else None
                ),
                "averageR": (
                    round(
                        sum(setup_actual_r[setup])
                        / len(setup_actual_r[setup]),
                        6,
                    )
                    if setup_actual_r.get(setup)
                    else None
                ),
                "expectancy": (
                    round(
                        sum(setup_actual_r[setup])
                        / len(setup_actual_r[setup]),
                        6,
                    )
                    if setup_actual_r.get(setup)
                    else None
                ),
            },
        }
        for setup, count in sorted(setup_sample_counts.items())
    ]

    holding_durations: list[float] = []

    for trade in trades:
        anchor_time = trade.get("chartAnchorTime")
        outcome_time = trade.get("outcomeEvidenceTime")

        if (
            isinstance(anchor_time, bool)
            or not isinstance(anchor_time, (int, float))
        ):
            continue

        if (
            isinstance(outcome_time, bool)
            or not isinstance(outcome_time, (int, float))
        ):
            continue

        if not all(
            isinstance(value, (int, float)) and value == value
            for value in (anchor_time, outcome_time)
        ):
            continue

        duration_seconds = (outcome_time - anchor_time) / 1000

        if duration_seconds <= 0:
            continue

        holding_durations.append(duration_seconds)

    sorted_holding_durations = sorted(holding_durations)

    holding_duration_median = (
        sorted_holding_durations[len(sorted_holding_durations) // 2]
        if len(sorted_holding_durations) % 2
        else (
            sorted_holding_durations[len(sorted_holding_durations) // 2 - 1]
            + sorted_holding_durations[len(sorted_holding_durations) // 2]
        ) / 2
        if sorted_holding_durations
        else None
    )

    planned_r: list[float] = []
    actual_r: list[float] = []
    actual_r_trades: list[tuple[str, float, str]] = []

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
        actual_r_trades.append(
            (trade.get("result"), realized_r, trade.get("timestamp"))
        )

    chronological_actual_r = [
        realized_r
        for _, realized_r, _ in sorted(
            actual_r_trades,
            key=lambda item: item[2] or "",
        )
    ]

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for realized_r in chronological_actual_r:
        equity += realized_r
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    chronological_results = [
        trade.get("result")
        for trade in sorted(
            trades,
            key=lambda trade: trade.get("timestamp") or "",
        )
    ]

    current_win_streak = 0
    max_win_streak = 0

    for result in chronological_results:
        if result == "WIN":
            current_win_streak += 1
            max_win_streak = max(max_win_streak, current_win_streak)
        else:
            current_win_streak = 0

    current_loss_streak = 0
    max_loss_streak = 0

    for result in chronological_results:
        if result == "LOSS":
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        else:
            current_loss_streak = 0

    winning_actual_r = [
        realized_r
        for _, realized_r, _ in actual_r_trades
        if realized_r > 0
    ]
    losing_actual_r = [
        realized_r
        for _, realized_r, _ in actual_r_trades
        if realized_r < 0
    ]

    biggest_winner = max(winning_actual_r) if winning_actual_r else None
    biggest_loser = min(losing_actual_r) if losing_actual_r else None

    gross_profit = sum(
        winning_actual_r
    )
    gross_loss = abs(sum(
        realized_r
        for _, realized_r, _ in actual_r_trades
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
                    for result, _, _ in actual_r_trades
                ),
                "losses": sum(
                    result == "LOSS"
                    for result, _, _ in actual_r_trades
                ),
                "breakEven": sum(
                    result == "BE"
                    for result, _, _ in actual_r_trades
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
        "biggestLoser": {
            "value": (
                round(biggest_loser, 6)
                if biggest_loser is not None
                else None
            ),
            "count": len(losing_actual_r),
        },
        "drawdown": {
            "value": round(max_drawdown, 6),
            "count": len(chronological_actual_r),
        },
        "winStreak": {
            "value": max_win_streak,
            "count": len(chronological_results),
        },
        "lossStreak": {
            "value": max_loss_streak,
            "count": len(chronological_results),
        },
        "holdingDuration": {
            "value": (
                round(
                    sum(holding_durations) / len(holding_durations),
                    6,
                )
                if holding_durations
                else None
            ),
            "median": (
                round(holding_duration_median, 6)
                if holding_duration_median is not None
                else None
            ),
            "count": len(holding_durations),
        },
        "byHour": by_hour,
        "byDay": by_day,
        "byWeek": by_week,
        "byMonth": by_month,
        "bySession": by_session,
        "setupPerformance": setup_performance,
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

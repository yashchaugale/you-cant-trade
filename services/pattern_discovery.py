"""Deterministic journal-level pattern discovery for You Can't Trade."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


PATTERN_DISCOVERY_VERSION = 3
MIN_PATTERN_SAMPLE = 3


def _actual_r(trade: dict[str, Any]) -> float | None:
    features = (
        (trade.get("intelligence") or {})
        .get("calculated", {})
        .get("features", {})
    )
    value = features.get("actualR")
    return float(value) if isinstance(value, (int, float)) else None


def _baseline_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    outcome_trades = [
        trade
        for trade in trades
        if trade.get("result") in {"WIN", "LOSS", "BE"}
    ]

    wins = sum(trade.get("result") == "WIN" for trade in outcome_trades)
    losses = sum(trade.get("result") == "LOSS" for trade in outcome_trades)
    decided = wins + losses

    actual_r_trade_ids: list[str] = []
    actual_r: list[float] = []

    for trade in outcome_trades:
        actual_r_value = _actual_r(trade)
        if actual_r_value is None:
            continue

        actual_r.append(actual_r_value)

        trade_id = trade.get("id")
        if isinstance(trade_id, str) and trade_id.strip():
            actual_r_trade_ids.append(trade_id)

    outcome_trade_ids = [
        trade["id"]
        for trade in outcome_trades
        if isinstance(trade.get("id"), str) and trade.get("id").strip()
    ]

    return {
        "sampleSize": len(outcome_trades),
        "winRate": (
            round(wins / decided, 6)
            if decided
            else None
        ),
        "tradeIds": outcome_trade_ids,
        "actualR": {
            "count": len(actual_r),
            "average": (
                round(sum(actual_r) / len(actual_r), 6)
                if actual_r
                else None
            ),
            "tradeIds": actual_r_trade_ids,
        },
    }


def _pattern_values(trade: dict[str, Any]) -> list[tuple[str, str]]:
    intelligence = trade.get("intelligence") or {}
    context = intelligence.get("marketContext") or {}
    structure = intelligence.get("marketStructure") or {}
    fingerprint = intelligence.get("setupFingerprint") or {}

    values: list[tuple[str, str]] = []

    candidates = [
        ("setup", trade.get("setup")),
        ("direction", trade.get("direction")),
        ("session", trade.get("session")),
        ("market_regime", context.get("regime")),
        ("structure_state", structure.get("state")),
    ]

    for dimension, value in candidates:
        if isinstance(value, str) and value.strip():
            values.append((dimension, value.strip()))

    timestamp = trade.get("timestamp")
    if isinstance(timestamp, str) and timestamp.strip():
        try:
            parsed_timestamp = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
            utc_timestamp = parsed_timestamp.astimezone(timezone.utc)
            values.append(("day", utc_timestamp.strftime("%A")))
        except ValueError:
            pass

    for value in fingerprint.get("features") or []:
        if isinstance(value, str) and value.strip():
            values.append(("fingerprint_feature", value.strip()))

    for value in fingerprint.get("tags") or []:
        if isinstance(value, str) and value.strip():
            values.append(("fingerprint_tag", value.strip()))

    return values


def discover_patterns(
    trades: list[dict[str, Any]],
    min_sample: int = MIN_PATTERN_SAMPLE,
) -> list[dict[str, Any]]:
    """Discover recurring outcome patterns from reviewed canonical trades."""
    if min_sample < 1:
        raise ValueError("min_sample must be at least 1.")

    baseline = _baseline_metrics(trades)

    journal_timestamps = [
        trade.get("timestamp")
        for trade in trades
        if trade.get("result") in {"WIN", "LOSS", "BE"}
        and isinstance(trade.get("timestamp"), str)
        and trade.get("timestamp").strip()
    ]
    journal_latest_observed = (
        max(journal_timestamps)
        if journal_timestamps
        else None
    )

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for trade in trades:
        if trade.get("result") not in {"WIN", "LOSS", "BE"}:
            continue

        for key in _pattern_values(trade):
            groups[key].append(trade)

    findings: list[dict[str, Any]] = []

    for (dimension, value), matches in groups.items():
        if len(matches) < min_sample:
            continue

        wins = sum(trade.get("result") == "WIN" for trade in matches)
        losses = sum(trade.get("result") == "LOSS" for trade in matches)
        break_even = sum(trade.get("result") == "BE" for trade in matches)

        actual_r = [
            actual_r_value
            for trade in matches
            if (actual_r_value := _actual_r(trade)) is not None
        ]

        timestamps = [
            trade.get("timestamp")
            for trade in matches
            if isinstance(trade.get("timestamp"), str)
        ]

        pattern_win_rate = round(wins / (wins + losses), 6) if wins + losses else None
        pattern_average_r = (
            round(sum(actual_r) / len(actual_r), 6)
            if actual_r
            else None
        )
        pattern_expectancy = pattern_average_r

        monthly_actual_r: dict[tuple[int, int], list[float]] = defaultdict(list)
        observed_months: set[tuple[int, int]] = set()

        for trade in matches:
            timestamp = trade.get("timestamp")
            if not isinstance(timestamp, str) or not timestamp.strip():
                continue

            try:
                parsed_timestamp = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )
            except ValueError:
                continue

            utc_timestamp = parsed_timestamp.astimezone(timezone.utc)
            month_key = (utc_timestamp.year, utc_timestamp.month)
            observed_months.add(month_key)

            trade_actual_r = _actual_r(trade)
            if trade_actual_r is not None:
                monthly_actual_r[month_key].append(trade_actual_r)

        profitable_periods = 0
        losing_periods = 0
        neutral_periods = 0

        for month_actual_r in monthly_actual_r.values():
            average_month_r = sum(month_actual_r) / len(month_actual_r)

            if average_month_r > 0:
                profitable_periods += 1
            elif average_month_r < 0:
                losing_periods += 1
            else:
                neutral_periods += 1

        age_in_days = None
        if journal_latest_observed is not None and timestamps:
            latest_observed = max(timestamps)
            try:
                latest_dt = datetime.fromisoformat(
                    latest_observed.replace("Z", "+00:00")
                )
                journal_latest_dt = datetime.fromisoformat(
                    journal_latest_observed.replace("Z", "+00:00")
                )
                age_in_days = (
                    journal_latest_dt - latest_dt
                ).total_seconds() / 86400
                age_in_days = round(age_in_days, 6)
            except ValueError:
                age_in_days = None

        findings.append(
            {
                "dimension": dimension,
                "value": value,
                "sampleSize": len(matches),
                "outcomes": {
                    "wins": wins,
                    "losses": losses,
                    "breakEven": break_even,
                },
                "winRate": pattern_win_rate,
                "expectancy": pattern_expectancy,
                "actualR": {
                    "count": len(actual_r),
                    "total": round(sum(actual_r), 6),
                    "average": pattern_average_r,
                },
                "baseline": {
                    "sampleSize": baseline["sampleSize"],
                    "winRate": baseline["winRate"],
                    "expectancy": baseline["actualR"]["average"],
                    "tradeIds": baseline["tradeIds"],
                    "actualR": baseline["actualR"],
                },
                "difference": {
                    "winRate": (
                        round(pattern_win_rate - baseline["winRate"], 6)
                        if pattern_win_rate is not None
                        and baseline["winRate"] is not None
                        else None
                    ),
                    "averageR": (
                        round(pattern_average_r - baseline["actualR"]["average"], 6)
                        if pattern_average_r is not None
                        and baseline["actualR"]["average"] is not None
                        else None
                    ),
                    "expectancy": (
                        round(
                            pattern_expectancy - baseline["actualR"]["average"],
                            6,
                        )
                        if pattern_expectancy is not None
                        and baseline["actualR"]["average"] is not None
                        else None
                    ),
                },
                "sourceTradeIds": [
                    trade.get("id")
                    for trade in matches
                    if isinstance(trade.get("id"), str)
                ],
                "firstObserved": min(timestamps) if timestamps else None,
                "lastObserved": max(timestamps) if timestamps else None,
                "recency": {
                    "lastObserved": max(timestamps) if timestamps else None,
                    "journalLatestObserved": journal_latest_observed,
                    "ageInDays": age_in_days,
                },
                "stability": {
                    "observedPeriods": len(observed_months),
                    "profitablePeriods": profitable_periods,
                    "losingPeriods": losing_periods,
                    "neutralPeriods": neutral_periods,
                    "periodsWithActualR": len(monthly_actual_r),
                },
                "computationVersion": PATTERN_DISCOVERY_VERSION,
                "evidenceStrength": {
                    "sampleSize": len(matches),
                    "actualRCoverage": (
                        round(len(actual_r) / len(matches), 6)
                        if matches
                        else 0.0
                    ),
                    "observedPeriods": len(observed_months),
                    "periodsWithActualR": len(monthly_actual_r),
                    "recent": (
                        age_in_days is not None
                        and age_in_days <= 30
                    ),
                    "level": (
                        "LOW"
                        if len(matches) < 10
                        else (
                            "MODERATE"
                            if len(observed_months) >= 3
                            and len(monthly_actual_r) >= 2
                            else "LOW"
                        )
                    ),
                    "minimumSample": min_sample,
                },
                "reliability": {
                    "level": "LOW" if len(matches) < 10 else "OBSERVATIONAL",
                    "minimumSample": min_sample,
                },
            }
        )

    return sorted(
        findings,
        key=lambda finding: (
            -finding["sampleSize"],
            finding["dimension"],
            finding["value"],
        ),
    )

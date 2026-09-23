"""Deterministic historical period comparison for You Can't Trade."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from services.pattern_discovery import MIN_PATTERN_SAMPLE, _actual_r


COMPARE_VERSION = 1

DEFAULT_CURRENT_COUNT = 30
DEFAULT_PREVIOUS_COUNT = 100

DISTRIBUTION_FIELDS = (
    "setup",
    "session",
    "direction",
    "behavior",
    "execution",
)


def _normalise_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _timestamp_key(trade: dict[str, Any]) -> tuple[int, str, str]:
    timestamp = trade.get("timestamp")
    if isinstance(timestamp, str) and timestamp.strip():
        raw = timestamp.strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (0, parsed.astimezone(timezone.utc).isoformat(), str(trade.get("id", "")))
        except ValueError:
            pass

    return (1, str(timestamp or ""), str(trade.get("id", "")))


def _chronological_trades(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(trades, key=_timestamp_key)


def select_periods(
    trades: list[dict[str, Any]],
    current_count: int = DEFAULT_CURRENT_COUNT,
    previous_count: int = DEFAULT_PREVIOUS_COUNT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (current, previous) non-overlapping chronological periods."""

    current_count = int(current_count)
    previous_count = int(previous_count)

    if current_count < 1:
        raise ValueError("current_count must be at least 1")
    if previous_count < 1:
        raise ValueError("previous_count must be at least 1")

    ordered = _chronological_trades(trades)

    current = ordered[-current_count:] if ordered else []
    current_start = max(0, len(ordered) - current_count)
    previous_start = max(0, current_start - previous_count)
    previous = ordered[previous_start:current_start]

    return current, previous


def _outcome_trades(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        trade
        for trade in trades
        if trade.get("result") in {"WIN", "LOSS"}
    ]


def _performance(trades: list[dict[str, Any]]) -> dict[str, Any]:
    outcome_trades = _outcome_trades(trades)
    wins = sum(trade.get("result") == "WIN" for trade in outcome_trades)
    losses = sum(trade.get("result") == "LOSS" for trade in outcome_trades)

    win_rate = (
        round(wins / (wins + losses), 6)
        if wins + losses
        else None
    )

    actual_r_values: list[float] = []
    actual_r_trade_ids: list[str] = []

    for trade in trades:
        value = _actual_r(trade)
        if value is not None:
            actual_r_values.append(value)
            actual_r_trade_ids.append(str(trade.get("id")))

    average_r = (
        round(sum(actual_r_values) / len(actual_r_values), 6)
        if actual_r_values
        else None
    )

    actual_r_coverage = (
        round(len(actual_r_values) / len(trades), 6)
        if trades
        else 0.0
    )

    return {
        "sampleSize": len(trades),
        "outcomeSampleSize": len(outcome_trades),
        "winRate": win_rate,
        "actualR": {
            "count": len(actual_r_values),
            "average": average_r,
            "coverage": actual_r_coverage,
            "tradeIds": actual_r_trade_ids,
        },
        "averageR": average_r,
        "expectancy": average_r,
    }


def _behavior_values(trade: dict[str, Any]) -> list[str]:
    intelligence = trade.get("intelligence")
    if not isinstance(intelligence, dict):
        return []

    behavior = intelligence.get("behavior")
    if not isinstance(behavior, dict):
        return []

    values: list[str] = []

    for key in ("tags", "ruleViolations"):
        items = behavior.get(key)
        if not isinstance(items, list):
            continue

        for item in items:
            value = _normalise_string(item)
            if value and value not in values:
                values.append(value)

    return values


def _distribution_values(
    trade: dict[str, Any],
    field: str,
) -> list[str]:
    if field == "behavior":
        return _behavior_values(trade)

    if field == "execution":
        value = _normalise_string(trade.get("executionTag"))
        return [value] if value else []

    value = _normalise_string(trade.get(field))
    return [value] if value else []


def _distribution(
    trades: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    trade_ids: dict[str, list[str]] = defaultdict(list)

    for trade in trades:
        trade_id = str(trade.get("id"))
        for value in _distribution_values(trade, field):
            counts[value] += 1
            if trade_id not in trade_ids[value]:
                trade_ids[value].append(trade_id)

    total = sum(counts.values())

    values = []
    for value in sorted(counts):
        count = counts[value]
        values.append(
            {
                "value": value,
                "count": count,
                "percentage": round(count / total, 6) if total else None,
                "tradeIds": trade_ids[value],
            }
        )

    return {
        "field": field,
        "sampleSize": len(trades),
        "categorySampleSize": total,
        "values": values,
    }


def _compare_distribution(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    current_distribution = _distribution(current, field)
    previous_distribution = _distribution(previous, field)

    current_by_value = {
        item["value"]: item for item in current_distribution["values"]
    }
    previous_by_value = {
        item["value"]: item for item in previous_distribution["values"]
    }

    all_values = sorted(
        set(current_by_value) | set(previous_by_value)
    )

    values = []

    for value in all_values:
        current_item = current_by_value.get(value)
        previous_item = previous_by_value.get(value)

        current_percentage = (
            current_item["percentage"] if current_item else 0.0
        )
        previous_percentage = (
            previous_item["percentage"] if previous_item else 0.0
        )

        values.append(
            {
                "value": value,
                "current": {
                    "count": current_item["count"] if current_item else 0,
                    "percentage": current_percentage,
                    "tradeIds": current_item["tradeIds"] if current_item else [],
                },
                "previous": {
                    "count": previous_item["count"] if previous_item else 0,
                    "percentage": previous_percentage,
                    "tradeIds": previous_item["tradeIds"] if previous_item else [],
                },
                "percentagePointChange": round(
                    current_percentage - previous_percentage,
                    6,
                ),
            }
        )

    return {
        "field": field,
        "currentSampleSize": len(current),
        "previousSampleSize": len(previous),
        "values": values,
    }


def _numeric_change(
    current: float | None,
    previous: float | None,
) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 6)


def _performance_comparison(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> dict[str, Any]:
    current_metrics = _performance(current)
    previous_metrics = _performance(previous)

    return {
        "sampleSize": {
            "current": len(current),
            "previous": len(previous),
            "change": len(current) - len(previous),
        },
        "winRate": {
            "current": current_metrics["winRate"],
            "previous": previous_metrics["winRate"],
            "change": _numeric_change(
                current_metrics["winRate"],
                previous_metrics["winRate"],
            ),
        },
        "averageR": {
            "current": current_metrics["averageR"],
            "previous": previous_metrics["averageR"],
            "change": _numeric_change(
                current_metrics["averageR"],
                previous_metrics["averageR"],
            ),
        },
        "expectancy": {
            "current": current_metrics["expectancy"],
            "previous": previous_metrics["expectancy"],
            "change": _numeric_change(
                current_metrics["expectancy"],
                previous_metrics["expectancy"],
            ),
        },
        "actualR": {
            "current": current_metrics["actualR"],
            "previous": previous_metrics["actualR"],
            "averageRChange": _numeric_change(
                current_metrics["actualR"]["average"],
                previous_metrics["actualR"]["average"],
            ),
        },
    }


def _pattern_key(pattern: dict[str, Any]) -> str:
    return f'{pattern.get("type")}::{pattern.get("value")}'


def _discover_period_patterns(
    trades: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Reuse the existing pattern taxonomy and threshold without making Compare
    authoritative over pattern discovery internals.
    """
    from services.pattern_discovery import discover_patterns

    patterns = discover_patterns(
        trades,
        min_sample=MIN_PATTERN_SAMPLE,
    )

    return {
        _pattern_key(pattern): pattern
        for pattern in patterns
    }


def _pattern_changes(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> dict[str, Any]:
    current_patterns = _discover_period_patterns(current)
    previous_patterns = _discover_period_patterns(previous)

    current_keys = set(current_patterns)
    previous_keys = set(previous_patterns)

    new_keys = sorted(current_keys - previous_keys)
    disappearing_keys = sorted(previous_keys - current_keys)

    return {
        "newPatterns": [
            current_patterns[key]
            for key in new_keys
        ],
        "disappearingPatterns": [
            previous_patterns[key]
            for key in disappearing_keys
        ],
    }


def _largest_distribution_change(
    distributions: dict[str, dict[str, Any]],
    direction: str,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []

    for field, comparison in distributions.items():
        for value in comparison["values"]:
            change = value["percentagePointChange"]

            if direction == "increase" and change <= 0:
                continue
            if direction == "decrease" and change >= 0:
                continue

            candidates.append(
                {
                    "field": field,
                    "value": value["value"],
                    "percentagePointChange": change,
                    "current": value["current"],
                    "previous": value["previous"],
                }
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            -abs(item["percentagePointChange"]),
            item["field"],
            item["value"],
        )
    )

    return candidates[0]


def _change_summary(
    performance: dict[str, Any],
    distributions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    increases: list[dict[str, Any]] = []
    decreases: list[dict[str, Any]] = []

    for metric in ("winRate", "averageR", "expectancy"):
        change = performance[metric]["change"]

        if change is None:
            continue

        item = {
            "field": metric,
            "change": change,
            "current": performance[metric]["current"],
            "previous": performance[metric]["previous"],
        }

        if change > 0:
            increases.append(item)
        elif change < 0:
            decreases.append(item)

    if increases:
        increases.sort(
            key=lambda item: (-abs(item["change"]), item["field"])
        )

    if decreases:
        decreases.sort(
            key=lambda item: (-abs(item["change"]), item["field"])
        )

    distribution_increase = _largest_distribution_change(
        distributions,
        "increase",
    )
    distribution_decrease = _largest_distribution_change(
        distributions,
        "decrease",
    )

    return {
        "largestMetricIncrease": increases[0] if increases else None,
        "largestMetricDecrease": decreases[0] if decreases else None,
        "largestDistributionIncrease": distribution_increase,
        "largestDistributionDecrease": distribution_decrease,
    }


def compare_periods(
    trades: list[dict[str, Any]],
    current_count: int = DEFAULT_CURRENT_COUNT,
    previous_count: int = DEFAULT_PREVIOUS_COUNT,
) -> dict[str, Any]:
    """Build the complete deterministic comparison."""

    current, previous = select_periods(
        trades,
        current_count=current_count,
        previous_count=previous_count,
    )

    performance = _performance_comparison(current, previous)

    distributions = {
        field: _compare_distribution(
            current,
            previous,
            field,
        )
        for field in DISTRIBUTION_FIELDS
    }

    pattern_changes = _pattern_changes(current, previous)

    return {
        "version": COMPARE_VERSION,
        "periods": {
            "current": {
                "definition": "LAST_N_TRADES",
                "requestedCount": int(current_count),
                "actualCount": len(current),
                "tradeIds": [
                    str(trade.get("id"))
                    for trade in current
                ],
            },
            "previous": {
                "definition": "PREVIOUS_N_TRADES",
                "requestedCount": int(previous_count),
                "actualCount": len(previous),
                "tradeIds": [
                    str(trade.get("id"))
                    for trade in previous
                ],
            },
        },
        "performance": performance,
        "distributions": distributions,
        "changes": _change_summary(
            performance,
            distributions,
        ),
        "patterns": pattern_changes,
    }

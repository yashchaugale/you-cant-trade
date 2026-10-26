"""Deterministic Current Understanding composition for You Can't Trade.

This module composes existing deterministic analytics into a small,
traceable description of the trader's current recorded evidence.

It does not predict, recommend, infer causality, or use AI-generated evidence.
"""

from __future__ import annotations

import math

from typing import Any


VERSION = 1

EVIDENCE_ORDER = {
    "INSUFFICIENT": 0,
    "LIMITED": 1,
    "MODERATE": 2,
    "STRONG": 3,
    "NONE": 0,
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _evidence_level(pattern: dict[str, Any]) -> str:
    evidence = pattern.get("evidenceStrength") or {}

    if isinstance(evidence, dict):
        level = evidence.get("level")
        if isinstance(level, str) and level.strip():
            normalized = level.strip().upper()

            # Pattern Discovery's public contract uses LOW/MODERATE.
            # Translate LOW to LIMITED for the shared understanding contract.
            if normalized == "LOW":
                return "LIMITED"

            if normalized in EVIDENCE_ORDER:
                return normalized

    return "INSUFFICIENT"


def _pattern_candidates(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []

    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        sample_size = pattern.get("sampleSize")
        if (
            not isinstance(sample_size, int)
            or isinstance(sample_size, bool)
            or sample_size < 3
        ):
            continue

        evidence_strength = pattern.get("evidenceStrength")
        if evidence_strength is not None and not isinstance(evidence_strength, dict):
            continue
        evidence_strength = evidence_strength or {}

        coverage = evidence_strength.get("actualRCoverage", 0)
        if (
            not isinstance(coverage, (int, float))
            or isinstance(coverage, bool)
            or not math.isfinite(coverage)
            or coverage < 0
        ):
            continue

        actual_r = pattern.get("actualR")
        if actual_r is not None and not isinstance(actual_r, dict):
            continue

        average_r = actual_r.get("average") if actual_r else None
        if average_r is not None and (
            not isinstance(average_r, (int, float))
            or isinstance(average_r, bool)
            or not math.isfinite(average_r)
        ):
            continue

        win_rate = pattern.get("winRate")
        if win_rate is not None and (
            not isinstance(win_rate, (int, float))
            or isinstance(win_rate, bool)
            or not math.isfinite(win_rate)
            or not 0 <= win_rate <= 1
        ):
            continue

        trade_ids = pattern.get("sourceTradeIds")
        if trade_ids is not None and (
            not isinstance(trade_ids, list)
            or any(
                not isinstance(trade_id, str) or not trade_id.strip()
                for trade_id in trade_ids
            )
            or len(set(trade_ids)) != len(trade_ids)
        ):
            continue

        evidence = _evidence_level(pattern)

        candidates.append(
            {
                "pattern": pattern,
                "evidence": evidence,
                "evidenceRank": EVIDENCE_ORDER.get(evidence, 0),
                "sampleSize": sample_size,
                "actualRCoverage": float(coverage),
                "averageR": float(average_r) if average_r is not None else None,
            }
        )

    return candidates


def _select_observation(
    patterns: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = _pattern_candidates(patterns)

    if not candidates:
        return None

    # Evidence level is primary.
    # Within the same evidence level, prefer:
    # 1. greater Actual R coverage
    # 2. larger sample
    # 3. larger absolute observed average R
    # This is a deterministic evidence-selection rule, not a trading ranking.
    candidates.sort(
        key=lambda item: (
            item["evidenceRank"],
            item["actualRCoverage"],
            item["sampleSize"],
            abs(item["averageR"]) if item["averageR"] is not None else -1,
        ),
        reverse=True,
    )

    return candidates[0]


def _select_watch(
    leaks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = []

    for leak in leaks:
        if not isinstance(leak, dict):
            continue

        raw_count = leak.get("occurrenceCount")
        if (
            not isinstance(raw_count, int)
            or isinstance(raw_count, bool)
            or raw_count <= 0
        ):
            continue
        count = raw_count

        raw_r_impact = leak.get("rImpact")
        if (
            not isinstance(raw_r_impact, (int, float))
            or isinstance(raw_r_impact, bool)
            or not math.isfinite(raw_r_impact)
        ):
            continue
        r_impact = float(raw_r_impact)

        raw_coverage = leak.get("actualRCoverage", 0)
        if (
            not isinstance(raw_coverage, (int, float))
            or isinstance(raw_coverage, bool)
            or not math.isfinite(raw_coverage)
            or raw_coverage < 0
        ):
            continue

        # A Home "watch" should describe a measured negative impact.
        # Positive or unknown R impact remains available in Leak Map,
        # but should not be presented as a leak to watch.
        if r_impact is None or r_impact >= 0:
            continue

        evidence = str(leak.get("evidenceStrength") or "INSUFFICIENT").upper()

        candidates.append(
            {
                "leak": leak,
                "evidence": evidence,
                "evidenceRank": EVIDENCE_ORDER.get(evidence, 0),
                "occurrenceCount": count,
                "actualRCoverage": _number(leak.get("actualRCoverage")),
                "rImpact": r_impact,
            }
        )

    if not candidates:
        return None

    # Prefer measured evidence first, then frequency, then measured R impact.
    candidates.sort(
        key=lambda item: (
            item["evidenceRank"],
            item["occurrenceCount"],
            item["actualRCoverage"],
            abs(item["rImpact"]) if item["rImpact"] is not None else -1,
        ),
        reverse=True,
    )

    return candidates[0]


def _format_pattern_observation(selected: dict[str, Any]) -> dict[str, Any]:
    pattern = selected["pattern"]
    dimension = pattern.get("dimension") or "condition"
    value = pattern.get("value") or "recorded"

    sample = selected["sampleSize"]
    average_r = selected["averageR"]
    win_rate = pattern.get("winRate")

    context_map = {
        "day": f"{value} trades",
        "direction": f"{value} trades",
        "setup": f"{value} setup",
        "session": f"{value} session",
        "market_regime": f"{value} market-regime trades",
        "structure_state": f"{value} market-structure trades",
        "setup_session": f"{value} trades",
        "setup_direction": f"{value} trades",
    }

    context = context_map.get(
        dimension,
        f"{dimension}={value}",
    )

    if average_r is not None and average_r > 0:
        opening = f"The {context} is starting to stand out."
        statement = (
            f"{opening} Across {sample} trades, you're averaging "
            f"{average_r:+.2f}R."
        )
    elif average_r is not None and average_r < 0:
        opening = f"The {context} is starting to stand out for the wrong reason."
        statement = (
            f"{opening} Across {sample} trades, you're averaging "
            f"{average_r:+.2f}R."
        )
    elif win_rate is not None:
        opening = f"Your {context} are starting to stand out."
        statement = (
            f"{opening} You've taken {sample} and won "
            f"{float(win_rate) * 100:.0f}% of them."
        )
    else:
        opening = f"Your {context} hasn't shown a clear pattern yet."
        statement = (
            f"{opening} Across {sample} trades, you've seen "
            "a mixed set of historical results."
        )

    return {
        "type": "PATTERN",
        "statement": statement,
        "evidenceStrength": selected["evidence"],
        "sampleSize": sample,
        "supportingTradeIds": list(pattern.get("sourceTradeIds") or []),
        "source": {
            "dimension": dimension,
            "value": value,
            "computationVersion": pattern.get(
                "computationVersion"
            ),
        },
    }


def _format_leak_watch(selected: dict[str, Any]) -> dict[str, Any]:
    leak = selected["leak"]

    label = leak.get("label") or leak.get("type") or "This leak"
    count = selected["occurrenceCount"]
    r_impact = selected["rImpact"]

    if r_impact is not None:
        statement = (
            f"{label} has appeared {count} times in your recorded trades, "
            f"with {r_impact:+.2f}R of measured R impact."
        )
    else:
        statement = (
            f"{label} has appeared {count} times in your recorded trades."
        )

    return {
        "type": "LEAK",
        "statement": statement,
        "evidenceStrength": selected["evidence"],
        "sampleSize": count,
        "supportingTradeIds": list(leak.get("supportingTradeIds") or []),
        "source": {
            "type": leak.get("type"),
            "computationVersion": leak.get("version"),
        },
    }


def _format_change(compare: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(compare, dict):
        return None

    performance = compare.get("performance")
    periods = compare.get("periods")

    if not isinstance(performance, dict) or not isinstance(periods, dict):
        return None

    average_r = performance.get("averageR")
    if not isinstance(average_r, dict):
        return None

    current = periods.get("current")
    previous = periods.get("previous")

    if not isinstance(current, dict) or not isinstance(previous, dict):
        return None

    current_r = average_r.get("current")
    previous_r = average_r.get("previous")
    change_r = average_r.get("change")

    current_count = current.get("actualCount", 0)
    previous_count = previous.get("actualCount", 0)

    if (
        not isinstance(current_count, int)
        or isinstance(current_count, bool)
        or not isinstance(previous_count, int)
        or isinstance(previous_count, bool)
        or current_count < 10
        or previous_count < 10
        or not isinstance(current_r, (int, float))
        or isinstance(current_r, bool)
        or not isinstance(previous_r, (int, float))
        or isinstance(previous_r, bool)
        or not isinstance(change_r, (int, float))
        or isinstance(change_r, bool)
        or not math.isfinite(current_r)
        or not math.isfinite(previous_r)
        or not math.isfinite(change_r)
        or not math.isclose(
            change_r,
            current_r - previous_r,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
        or abs(change_r) < 0.3
    ):
        return None

    current_trade_ids = current.get("tradeIds")
    previous_trade_ids = previous.get("tradeIds")

    if (
        not isinstance(current_trade_ids, list)
        or not isinstance(previous_trade_ids, list)
        or len(current_trade_ids) != current_count
        or len(previous_trade_ids) != previous_count
        or any(
            not isinstance(trade_id, str) or not trade_id.strip()
            for trade_id in current_trade_ids + previous_trade_ids
        )
        or len(set(current_trade_ids)) != len(current_trade_ids)
        or len(set(previous_trade_ids)) != len(previous_trade_ids)
        or set(current_trade_ids) & set(previous_trade_ids)
    ):
        return None

    statement = (
        f"Your latest {current.get('actualCount')} trades are averaging "
        f"{float(current_r):+.2f}R, up from "
        f"{float(previous_r):+.2f}R in the trades before them."
    )

    return {
        "type": "COMPARE",
        "statement": statement,
        "supportingTradeIds": current_trade_ids + previous_trade_ids,
        "source": {
            "version": compare.get("version"),
            "currentCount": current.get("actualCount"),
            "previousCount": previous.get("actualCount"),
        },
    }



def _build_pattern_finding(
    selected: dict[str, Any],
) -> dict[str, Any]:
    pattern = selected["pattern"]

    dimension = pattern.get("dimension") or "condition"
    value = pattern.get("value") or "recorded"
    sample_size = selected["sampleSize"]
    average_r = selected["averageR"]

    title = f"{value} trades are standing out"

    if average_r is not None and average_r > 0:
        summary = (
            f"Your {value} trades are averaging "
            f"{average_r:+.2f}R across {sample_size} trades."
        )
    elif average_r is not None and average_r < 0:
        summary = (
            f"Your {value} trades are averaging "
            f"{average_r:+.2f}R across {sample_size} trades."
        )
    else:
        summary = (
            f"Your {value} trades have been observed "
            f"{sample_size} times."
        )

    trade_ids = list(pattern.get("sourceTradeIds") or [])

    return {
        "id": f"PATTERN::{dimension}::{value}",
        "type": "NEW_PATTERN",
        "status": "SUPPORTED",
        "priority": None,
        "title": title,
        "summary": summary,
        "confidence": selected["evidence"],
        "sampleSize": sample_size,
        "evidence": {
            "sampleSize": sample_size,
            "metrics": {
                "averageR": average_r,
                "winRate": pattern.get("winRate"),
                "difference": pattern.get("difference") or {},
            },
            "tradeIds": trade_ids,
            "source": "pattern_discovery",
        },
        "source": {
            "engine": "pattern_discovery",
            "computationVersion": pattern.get("computationVersion"),
            "dimension": dimension,
            "value": value,
        },
        "supportingTradeIds": trade_ids,
        "relatedMemory": None,
        "relatedExperiment": None,
    }


def _build_performance_change_finding(
    compare: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(compare, dict):
        return None

    periods = compare.get("periods")
    performance = compare.get("performance")
    if not isinstance(periods, dict) or not isinstance(performance, dict):
        return None

    current = periods.get("current")
    previous = periods.get("previous")
    average_r = performance.get("averageR")

    if (
        not isinstance(current, dict)
        or not isinstance(previous, dict)
        or not isinstance(average_r, dict)
    ):
        return None

    current_r = average_r.get("current")
    previous_r = average_r.get("previous")
    change_r = average_r.get("change")
    current_count = current.get("actualCount")
    previous_count = previous.get("actualCount")

    if (
        not isinstance(current_count, int)
        or isinstance(current_count, bool)
        or current_count < 10
        or not isinstance(previous_count, int)
        or isinstance(previous_count, bool)
        or previous_count < 10
        or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            for value in (current_r, previous_r, change_r)
        )
        or abs(change_r) < 0.3
    ):
        return None

    current_trade_ids = current.get("tradeIds", [])
    previous_trade_ids = previous.get("tradeIds", [])

    if (
        not isinstance(current_trade_ids, list)
        or not isinstance(previous_trade_ids, list)
        or len(current_trade_ids) != current_count
        or len(previous_trade_ids) != previous_count
        or any(
            not isinstance(trade_id, str) or not trade_id.strip()
            for trade_id in current_trade_ids + previous_trade_ids
        )
        or len(set(current_trade_ids)) != len(current_trade_ids)
        or len(set(previous_trade_ids)) != len(previous_trade_ids)
        or set(current_trade_ids) & set(previous_trade_ids)
    ):
        return None

    trade_ids = current_trade_ids + previous_trade_ids
    direction = "improving" if change_r > 0 else "declining"

    summary = (
        f"Your latest {current_count} trades are averaging "
        f"{current_r:+.2f}R, compared with "
        f"{previous_r:+.2f}R in the previous {previous_count} trades."
    )

    return {
        "id": "PERFORMANCE_CHANGE::AVERAGE_R",
        "type": "PERFORMANCE_CHANGE",
        "status": "SUPPORTED",
        "priority": None,
        "title": f"Recent performance is {direction}",
        "summary": summary,
        "confidence": "MODERATE",
        "sampleSize": current_count,
        "evidence": {
            "sampleSize": current_count,
            "metrics": {
                "currentAverageR": current_r,
                "previousAverageR": previous_r,
                "changeR": change_r,
                "previousSampleSize": previous_count,
            },
            "tradeIds": trade_ids,
            "source": "compare",
        },
        "source": {
            "engine": "compare",
            "computationVersion": compare.get("version"),
        },
        "supportingTradeIds": trade_ids,
        "relatedMemory": None,
        "relatedExperiment": None,
    }


def _build_behavior_change_finding(
    compare: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(compare, dict):
        return None

    distributions = compare.get("distributions")
    if not isinstance(distributions, dict):
        return None

    behavior = distributions.get("behavior")
    if not isinstance(behavior, dict):
        return None

    values = behavior.get("values")
    current_sample_size = behavior.get("currentSampleSize")
    previous_sample_size = behavior.get("previousSampleSize")

    if (
        not isinstance(values, list)
        or not isinstance(current_sample_size, int)
        or isinstance(current_sample_size, bool)
        or current_sample_size < 10
        or not isinstance(previous_sample_size, int)
        or isinstance(previous_sample_size, bool)
        or previous_sample_size < 10
    ):
        return None

    candidates = []

    for item in values:
        if not isinstance(item, dict):
            continue

        change = item.get("percentagePointChange")
        current = item.get("current")
        previous = item.get("previous")
        value = item.get("value")

        if (
            not isinstance(change, (int, float))
            or isinstance(change, bool)
            or not math.isfinite(change)
            or abs(change) < 0.15
            or not isinstance(value, str)
            or not value.strip()
            or not isinstance(current, dict)
            or not isinstance(previous, dict)
        ):
            continue

        current_count = current.get("count")
        previous_count = previous.get("count")

        if (
            not isinstance(current_count, int)
            or isinstance(current_count, bool)
            or current_count < 0
            or not isinstance(previous_count, int)
            or isinstance(previous_count, bool)
            or previous_count < 0
        ):
            continue

        current_trade_ids = current.get("tradeIds", [])
        previous_trade_ids = previous.get("tradeIds", [])

        if (
            not isinstance(current_trade_ids, list)
            or not isinstance(previous_trade_ids, list)
            or len(current_trade_ids) != current_count
            or len(previous_trade_ids) != previous_count
            or current_count > current_sample_size
            or previous_count > previous_sample_size
            or current_count + previous_count < 10
            or any(
                not isinstance(trade_id, str) or not trade_id.strip()
                for trade_id in current_trade_ids + previous_trade_ids
            )
            or len(set(current_trade_ids)) != len(current_trade_ids)
            or len(set(previous_trade_ids)) != len(previous_trade_ids)
            or set(current_trade_ids) & set(previous_trade_ids)
        ):
            continue

        candidates.append({
            "item": item,
            "change": float(change),
            "current": current,
            "previous": previous,
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            abs(item["change"]),
            item["current"]["count"],
        ),
        reverse=True,
    )

    selected = candidates[0]
    item = selected["item"]
    value = item["value"]
    change = selected["change"]
    current = selected["current"]
    previous = selected["previous"]
    current_count = current["count"]
    previous_count = previous["count"]
    trade_ids = current.get("tradeIds", []) + previous.get("tradeIds", [])
    direction = "more often" if change > 0 else "less often"

    return {
        "id": f"BEHAVIOR_CHANGE::{value}",
        "type": "BEHAVIOR_CHANGE",
        "status": "SUPPORTED",
        "priority": None,
        "title": f"{value} is showing up {direction}",
        "summary": (
            f"{value} appeared {current_count} times in the current period "
            f"versus {previous_count} times in the previous period."
        ),
        "confidence": "MODERATE",
        "sampleSize": current_sample_size,
        "evidence": {
            "sampleSize": current_sample_size,
            "metrics": {
                "currentCount": current_count,
                "previousCount": previous_count,
                "percentagePointChange": change,
            },
            "tradeIds": trade_ids,
            "source": "compare",
        },
        "source": {
            "engine": "compare",
            "computationVersion": compare.get("version"),
            "dimension": "behavior",
            "value": value,
        },
        "supportingTradeIds": trade_ids,
        "relatedMemory": None,
        "relatedExperiment": None,
    }


def _build_weakening_pattern_finding(
    patterns: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = []

    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        sample_size = pattern.get("sampleSize")
        actual_r = pattern.get("actualR")
        average_r = actual_r.get("average") if isinstance(actual_r, dict) else None
        stability = pattern.get("stability")
        evidence = pattern.get("evidenceStrength")

        if (
            not isinstance(sample_size, int)
            or isinstance(sample_size, bool)
            or sample_size < 10
            or not isinstance(average_r, (int, float))
            or isinstance(average_r, bool)
            or not math.isfinite(average_r)
            or not isinstance(stability, dict)
            or not isinstance(evidence, dict)
        ):
            continue

        period_values = (
            stability.get("profitablePeriods"),
            stability.get("losingPeriods"),
            stability.get("observedPeriods"),
            stability.get("periodsWithActualR"),
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in period_values
        ):
            continue

        profitable_periods, losing_periods, observed_periods, periods_with_actual_r = period_values

        if (
            average_r >= 0
            or observed_periods < 3
            or periods_with_actual_r < 2
            or periods_with_actual_r > observed_periods
            or profitable_periods + losing_periods > observed_periods
            or losing_periods <= profitable_periods
            or str(evidence.get("level", "")).upper() == "LOW"
        ):
            continue

        candidates.append(pattern)

    if not candidates:
        return None

    candidates.sort(
        key=lambda pattern: (
            abs(float((pattern.get("actualR") or {}).get("average") or 0)),
            int(pattern.get("sampleSize") or 0),
            str(pattern.get("dimension") or ""),
            str(pattern.get("value") or ""),
        ),
        reverse=True,
    )

    pattern = candidates[0]

    dimension = pattern.get("dimension") or "condition"
    value = pattern.get("value") or "recorded"
    sample_size = int(pattern.get("sampleSize") or 0)
    average_r = float((pattern.get("actualR") or {}).get("average"))

    trade_ids = list(pattern.get("sourceTradeIds") or [])

    return {
        "id": f"WEAKENING_PATTERN::{dimension}::{value}",
        "type": "WEAKENING_PATTERN",
        "status": "SUPPORTED",
        "priority": None,
        "title": f"{value} pattern is weakening",
        "summary": (
            f"{value} is averaging {average_r:+.2f}R across "
            f"{sample_size} trades, with more losing than profitable "
            f"observed periods."
        ),
        "confidence": (pattern.get("evidenceStrength") or {}).get(
            "level",
            "MODERATE",
        ),
        "sampleSize": sample_size,
        "evidence": {
            "sampleSize": sample_size,
            "metrics": {
                "averageR": average_r,
                "profitablePeriods": int(
                    (pattern.get("stability") or {}).get(
                        "profitablePeriods", 0
                    )
                ),
                "losingPeriods": int(
                    (pattern.get("stability") or {}).get(
                        "losingPeriods", 0
                    )
                ),
                "observedPeriods": int(
                    (pattern.get("stability") or {}).get(
                        "observedPeriods", 0
                    )
                ),
            },
            "tradeIds": trade_ids,
            "source": "pattern_discovery",
        },
        "source": {
            "engine": "pattern_discovery",
            "computationVersion": pattern.get("computationVersion"),
            "dimension": dimension,
            "value": value,
        },
        "supportingTradeIds": trade_ids,
        "relatedMemory": None,
        "relatedExperiment": None,
    }



def _build_interesting_relationship_finding(
    compare: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(compare, dict):
        return None

    changes = compare.get("changes")
    if not isinstance(changes, dict):
        return None

    candidates = []

    for item in (
        changes.get("largestDistributionIncrease"),
        changes.get("largestDistributionDecrease"),
    ):
        if not isinstance(item, dict):
            continue

        change = item.get("percentagePointChange")
        current = item.get("current")
        previous = item.get("previous")
        field = item.get("field")
        value = item.get("value")

        if (
            not isinstance(change, (int, float))
            or isinstance(change, bool)
            or not math.isfinite(change)
            or abs(change) < 0.15
            or not isinstance(current, dict)
            or not isinstance(previous, dict)
            or not isinstance(field, str)
            or not field.strip()
            or not isinstance(value, str)
            or not value.strip()
        ):
            continue

        current_count = current.get("count")
        previous_count = previous.get("count")

        if (
            not isinstance(current_count, int)
            or isinstance(current_count, bool)
            or current_count < 0
            or not isinstance(previous_count, int)
            or isinstance(previous_count, bool)
            or previous_count < 0
            or current_count + previous_count < 10
        ):
            continue

        current_trade_ids = current.get("tradeIds", [])
        previous_trade_ids = previous.get("tradeIds", [])

        if (
            not isinstance(current_trade_ids, list)
            or not isinstance(previous_trade_ids, list)
            or any(
                not isinstance(trade_id, str) or not trade_id.strip()
                for trade_id in current_trade_ids + previous_trade_ids
            )
            or len(set(current_trade_ids)) != len(current_trade_ids)
            or len(set(previous_trade_ids)) != len(previous_trade_ids)
            or set(current_trade_ids) & set(previous_trade_ids)
        ):
            continue

        candidates.append(item)

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            -abs(item["percentagePointChange"]),
            item["field"],
            item["value"],
        )
    )

    selected = candidates[0]
    current = selected["current"]
    previous = selected["previous"]
    trade_ids = current.get("tradeIds", []) + previous.get("tradeIds", [])

    change = selected["percentagePointChange"]
    direction = "more" if change > 0 else "less"
    sample_size = current["count"] + previous["count"]

    return {
        "id": f"interesting_relationship:{selected['field']}:{selected['value']}",
        "type": "INTERESTING_RELATIONSHIP",
        "title": f"{selected['value']} is showing up {direction} often",
        "summary": (
            f"{selected['field']} changed by "
            f"{change:+.1f} percentage points between periods."
        ),
        "status": "SUPPORTED",
        "importance": "MODERATE",
        "confidence": "MODERATE",
        "sampleSize": sample_size,
        "evidence": {
            "sampleSize": sample_size,
            "metrics": {
                "currentCount": current["count"],
                "previousCount": previous["count"],
                "percentagePointChange": change,
            },
            "tradeIds": trade_ids,
            "source": "compare",
        },
        "reason": (
            f"{selected['field']}:{selected['value']} "
            f"changed noticeably between comparison periods."
        ),
        "relatedMemoryIds": [],
        "relatedExperimentIds": [],
        "source": {
            "engine": "compare",
            "computationVersion": compare.get("version"),
            "dimension": selected["field"],
            "value": selected["value"],
        },
        "supportingTradeIds": trade_ids,
    }


def _build_data_gap_finding(
    data_health: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(data_health, dict):
        return None

    total_trades = data_health.get("totalTrades")
    missing = data_health.get("missing")

    if (
        not isinstance(total_trades, int)
        or isinstance(total_trades, bool)
        or total_trades < 1
        or not isinstance(missing, dict)
    ):
        return None

    if any(
        not isinstance(field, str)
        or not field.strip()
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
        or count > total_trades
        for field, count in missing.items()
    ):
        return None

    candidates = [
        (field, count)
        for field, count in missing.items()
        if count > 0
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[1], item[0]))
    field, missing_count = candidates[0]

    return {
        "id": f"data_gap:{field}",
        "type": "DATA_GAP",
        "title": f"{field} is missing from some trades",
        "summary": (
            f"{missing_count} of {total_trades} trades "
            f"are missing {field}."
        ),
        "status": "SUPPORTED",
        "importance": "MODERATE",
        "confidence": "HIGH",
        "sampleSize": total_trades,
        "evidence": {
            "sampleSize": total_trades,
            "metrics": {
                "missingCount": missing_count,
                "totalTrades": total_trades,
            },
            "tradeIds": [],
            "source": "data_health",
        },
        "reason": (
            f"Data health reports {missing_count} trades "
            f"without {field}."
        ),
        "relatedMemoryIds": [],
        "relatedExperimentIds": [],
        "source": {
            "engine": "data_health",
            "computationVersion": data_health.get("computationVersion"),
            "dimension": field,
        },
        "supportingTradeIds": [],
    }


def _verify_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verified = []
    supported_types = {
        "NEW_PATTERN",
        "PERFORMANCE_CHANGE",
        "BEHAVIOR_CHANGE",
        "WEAKENING_PATTERN",
        "INTERESTING_RELATIONSHIP",
        "DATA_GAP",
    }
    expected_sources = {
        "NEW_PATTERN": "pattern_discovery",
        "PERFORMANCE_CHANGE": "compare",
        "BEHAVIOR_CHANGE": "compare",
        "WEAKENING_PATTERN": "pattern_discovery",
        "INTERESTING_RELATIONSHIP": "compare",
        "DATA_GAP": "data_health",
    }

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not finding_id.strip():
            continue

        finding_type = finding.get("type")
        if not isinstance(finding_type, str) or finding_type not in supported_types:
            continue

        evidence = finding.get("evidence")
        if not isinstance(evidence, dict):
            continue

        sample_size = evidence.get("sampleSize")
        metrics = evidence.get("metrics")
        trade_ids = evidence.get("tradeIds")
        source = evidence.get("source")

        if isinstance(sample_size, bool) or not isinstance(sample_size, int):
            continue

        if sample_size <= 0:
            continue

        if finding.get("type") == "NEW_PATTERN":
            finding_sample_size = finding.get("sampleSize")
            if (
                isinstance(finding_sample_size, bool)
                or not isinstance(finding_sample_size, int)
                or finding_sample_size != sample_size
            ):
                continue

        if not isinstance(metrics, dict):
            continue

        if not isinstance(trade_ids, list):
            continue

        if any(
            not isinstance(trade_id, str) or not trade_id.strip()
            for trade_id in trade_ids
        ):
            continue

        if len(trade_ids) != len(set(trade_ids)):
            continue

        def contains_non_finite_number(value: Any) -> bool:
            if isinstance(value, bool) or value is None:
                return False
            if isinstance(value, (int, float)):
                return not math.isfinite(value)
            if isinstance(value, dict):
                return any(contains_non_finite_number(item) for item in value.values())
            if isinstance(value, (list, tuple)):
                return any(contains_non_finite_number(item) for item in value)
            return False

        if contains_non_finite_number(metrics):
            continue

        if not isinstance(source, str) or not source.strip():
            continue

        if source != expected_sources[finding_type]:
            continue

        finding_sample_size = finding.get("sampleSize")
        if finding_sample_size is not None and (
            isinstance(finding_sample_size, bool)
            or not isinstance(finding_sample_size, int)
            or finding_sample_size != sample_size
        ):
            continue

        title = finding.get("title")
        summary = finding.get("summary")
        if title is not None and (
            not isinstance(title, str) or not title.strip()
        ):
            continue
        if summary is not None and (
            not isinstance(summary, str) or not summary.strip()
        ):
            continue

        verified.append(finding)

    return verified


def _prioritize_findings(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    type_rank = {
        "PERFORMANCE_CHANGE": 5,
        "WEAKENING_PATTERN": 4,
        "NEW_PATTERN": 3,
        "BEHAVIOR_CHANGE": 2,
        "INTERESTING_RELATIONSHIP": 1,
        "DATA_GAP": 0,
    }

    ranked = sorted(
        findings,
        key=lambda finding: (
            type_rank.get(finding.get("type"), 0),
            finding.get("sampleSize", 0),
            finding.get("id", ""),
        ),
        reverse=True,
    )

    for index, finding in enumerate(ranked, start=1):
        finding["priority"] = index

    return ranked


def build_current_understanding(
    *,
    trade_count: int,
    patterns: list[dict[str, Any]] | None = None,
    leaks: list[dict[str, Any]] | None = None,
    compare: dict[str, Any] | None = None,
    data_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose deterministic current understanding from existing evidence."""

    if (
        not isinstance(trade_count, int)
        or isinstance(trade_count, bool)
        or trade_count < 0
    ):
        raise ValueError("trade_count must be a non-negative integer")
    patterns = patterns if isinstance(patterns, list) else []
    leaks = leaks if isinstance(leaks, list) else []
    data_health = data_health if isinstance(data_health, dict) else None

    if trade_count == 0:
        return {
            "version": VERSION,
            "status": "NO_TRADES",
            "tradeCount": 0,
            "observation": None,
            "watch": None,
            "recentChange": None,
        }

    observation = _select_observation(patterns)
    watch = _select_watch(leaks)
    recent_change = _format_change(compare)

    pattern_finding = (
        _build_pattern_finding(observation)
        if observation is not None
        else None
    )
    performance_finding = _build_performance_change_finding(compare)
    behavior_finding = _build_behavior_change_finding(compare)
    weakening_finding = _build_weakening_pattern_finding(patterns)
    relationship_finding = _build_interesting_relationship_finding(compare)
    data_gap_finding = _build_data_gap_finding(data_health)

    # A pattern cannot be presented as both newly standing out and weakening
    # in the same understanding snapshot.
    if pattern_finding is not None and weakening_finding is not None:
        same_pattern = (
            pattern_finding["source"].get("dimension")
            == weakening_finding["source"].get("dimension")
            and pattern_finding["source"].get("value")
            == weakening_finding["source"].get("value")
        )
        if same_pattern:
            pattern_finding = None

    findings = [
        finding
        for finding in (
            pattern_finding,
            performance_finding,
            behavior_finding,
            weakening_finding,
            relationship_finding,
            data_gap_finding,
        )
        if finding is not None
    ]

    findings = _verify_findings(findings)
    findings = _prioritize_findings(findings)
    surfaced_findings = findings[:3]

    if observation is None:
        status = "LEARNING"
    else:
        status = "READY"

    return {
        "version": VERSION,
        "status": status,
        "tradeCount": trade_count,
        "observation": (
            _format_pattern_observation(observation)
            if observation is not None
            else None
        ),
        "watch": (
            _format_leak_watch(watch)
            if watch is not None
            else None
        ),
        "recentChange": recent_change,
        "findings": surfaced_findings,
    }

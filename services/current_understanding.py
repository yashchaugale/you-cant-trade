"""Deterministic Current Understanding composition for You Can't Trade.

This module composes existing deterministic analytics into a small,
traceable description of the trader's current recorded evidence.

It does not predict, recommend, infer causality, or use AI-generated evidence.
"""

from __future__ import annotations

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

        sample_size = int(_number(pattern.get("sampleSize"), 0))
        if sample_size < 3:
            continue

        evidence = _evidence_level(pattern)

        candidates.append(
            {
                "pattern": pattern,
                "evidence": evidence,
                "evidenceRank": EVIDENCE_ORDER.get(evidence, 0),
                "sampleSize": sample_size,
                "actualRCoverage": _number(
                    (pattern.get("evidenceStrength") or {}).get(
                        "actualRCoverage",
                        0,
                    )
                ),
                "averageR": (
                    _number((pattern.get("actualR") or {}).get("average"))
                    if (pattern.get("actualR") or {}).get("average") is not None
                    else None
                ),
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

        count = int(_number(leak.get("occurrenceCount"), 0))
        if count <= 0:
            continue

        r_impact = (
            _number(leak.get("rImpact"))
            if leak.get("rImpact") is not None
            else None
        )

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

    performance = compare.get("performance") or {}

    average_r = performance.get("averageR") or {}
    current_r = average_r.get("current")
    previous_r = average_r.get("previous")
    change_r = average_r.get("change")

    current = compare.get("periods", {}).get("current") or {}
    previous = compare.get("periods", {}).get("previous") or {}

    if (
        current.get("actualCount", 0) <= 0
        or previous.get("actualCount", 0) <= 0
        or change_r is None
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
        "supportingTradeIds": list(current.get("tradeIds") or [])
        + list(previous.get("tradeIds") or []),
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

    periods = compare.get("periods") or {}
    current = periods.get("current") or {}
    previous = periods.get("previous") or {}

    performance = compare.get("performance") or {}
    average_r = performance.get("averageR") or {}

    current_r = average_r.get("current")
    previous_r = average_r.get("previous")
    change_r = average_r.get("change")

    current_count = current.get("actualCount", 0)
    previous_count = previous.get("actualCount", 0)

    if (
        current_count <= 0
        or previous_count <= 0
        or change_r is None
        or current_r is None
        or previous_r is None
    ):
        return None

    current_trade_ids = list(current.get("tradeIds") or [])
    previous_trade_ids = list(previous.get("tradeIds") or [])
    trade_ids = current_trade_ids + previous_trade_ids

    direction = "improving" if float(change_r) > 0 else "declining"

    title = f"Recent performance is {direction}"

    summary = (
        f"Your latest {current_count} trades are averaging "
        f"{float(current_r):+.2f}R, compared with "
        f"{float(previous_r):+.2f}R in the previous {previous_count} trades."
    )

    return {
        "id": "PERFORMANCE_CHANGE::AVERAGE_R",
        "type": "PERFORMANCE_CHANGE",
        "status": "SUPPORTED",
        "priority": None,
        "title": title,
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

    distributions = compare.get("distributions") or {}
    behavior = distributions.get("behavior") or {}
    values = behavior.get("values") or []

    candidates = []

    for item in values:
        if not isinstance(item, dict):
            continue

        change = item.get("percentagePointChange")
        if change is None or change == 0:
            continue

        current = item.get("current") or {}
        previous = item.get("previous") or {}

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
            item["current"].get("count", 0),
        ),
        reverse=True,
    )

    selected = candidates[0]
    item = selected["item"]
    value = item.get("value") or "Behavior"
    change = selected["change"]

    current = selected["current"]
    previous = selected["previous"]

    current_count = current.get("count", 0)
    previous_count = previous.get("count", 0)

    trade_ids = list(
        dict.fromkeys(
            list(current.get("tradeIds") or [])
            + list(previous.get("tradeIds") or [])
        )
    )

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
        "sampleSize": current.get("count", 0),
        "evidence": {
            "sampleSize": behavior.get("currentSampleSize", 0),
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

        sample_size = int(pattern.get("sampleSize") or 0)
        average_r = (pattern.get("actualR") or {}).get("average")
        stability = pattern.get("stability") or {}
        evidence = pattern.get("evidenceStrength") or {}

        profitable_periods = int(stability.get("profitablePeriods") or 0)
        losing_periods = int(stability.get("losingPeriods") or 0)
        observed_periods = int(stability.get("observedPeriods") or 0)
        periods_with_actual_r = int(stability.get("periodsWithActualR") or 0)

        if (
            sample_size < 10
            or average_r is None
            or float(average_r) >= 0
            or observed_periods < 3
            or periods_with_actual_r < 2
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
    if not compare:
        return None

    changes = compare.get("changes", {})

    increase = changes.get("largestDistributionIncrease")
    decrease = changes.get("largestDistributionDecrease")

    candidates = [
        item
        for item in (increase, decrease)
        if item is not None
    ]

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

    trade_ids = list(
        dict.fromkeys(
            current.get("tradeIds", [])
            + previous.get("tradeIds", [])
        )
    )

    change = selected["percentagePointChange"]
    direction = "more" if change > 0 else "less"

    return {
        "id": (
            f"interesting_relationship:"
            f"{selected['field']}:{selected['value']}"
        ),
        "type": "INTERESTING_RELATIONSHIP",
        "title": (
            f"{selected['value']} is showing up {direction} often"
        ),
        "summary": (
            f"{selected['field']} changed by "
            f"{change:+.1f} percentage points between periods."
        ),
        "status": "SUPPORTED",
        "importance": "MODERATE",
        "confidence": "MODERATE",
        "sampleSize": (
            current.get("count", 0)
            + previous.get("count", 0)
        ),
        "evidence": {
            "sampleSize": (
                current.get("count", 0)
                + previous.get("count", 0)
            ),
            "metrics": {
                "currentCount": current.get("count"),
                "previousCount": previous.get("count"),
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


def _prioritize_findings(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    type_rank = {
        "PERFORMANCE_CHANGE": 3,
        "NEW_PATTERN": 2,
        "BEHAVIOR_CHANGE": 1,
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
) -> dict[str, Any]:
    """Compose deterministic current understanding from existing evidence."""

    trade_count = max(0, int(trade_count or 0))
    patterns = patterns if isinstance(patterns, list) else []
    leaks = leaks if isinstance(leaks, list) else []

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

    findings = [
        finding
        for finding in (
            pattern_finding,
            performance_finding,
            behavior_finding,
            weakening_finding,
            relationship_finding,
        )
        if finding is not None
    ]

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

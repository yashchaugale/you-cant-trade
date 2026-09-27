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
            f"{opening} Across {sample} trades, they've averaged "
            f"{average_r:+.2f}R."
        )
    elif average_r is not None and average_r < 0:
        opening = f"The {context} is starting to stand out for the wrong reason."
        statement = (
            f"{opening} Across {sample} trades, they've averaged "
            f"{average_r:+.2f}R."
        )
    elif win_rate is not None:
        opening = f"There's an early signal around your {context}."
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
        f"Across the latest {current.get('actualCount')} trades, "
        f"average actual R is {float(current_r):+.2f}R versus "
        f"{float(previous_r):+.2f}R in the preceding set "
        f"({float(change_r):+.2f}R change)."
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
    }

"""Deterministic historical leak detection."""

from __future__ import annotations

from typing import Any


LEAK_MAP_VERSION = 1

SUPPORTED_LEAK_TYPES = (
    "LATE_ENTRY",
    "EARLY_EXIT",
    "STOP_MOVEMENT",
    "RULE_VIOLATION",
    "COUNTER_STRUCTURE",
    "OVERTRADING",
    "REVENGE_TRADING",
)


def _intelligence(trade: dict[str, Any]) -> dict[str, Any]:
    value = trade.get("intelligence")
    return value if isinstance(value, dict) else {}


def _execution(trade: dict[str, Any]) -> dict[str, Any]:
    value = _intelligence(trade).get("execution")
    return value if isinstance(value, dict) else {}


def _behavior(trade: dict[str, Any]) -> dict[str, Any]:
    value = _intelligence(trade).get("behavior")
    return value if isinstance(value, dict) else {}


def _rules(trade: dict[str, Any]) -> dict[str, Any]:
    value = _intelligence(trade).get("rules")
    return value if isinstance(value, dict) else {}


def _fingerprint(trade: dict[str, Any]) -> dict[str, Any]:
    value = _intelligence(trade).get("setupFingerprint")
    return value if isinstance(value, dict) else {}


def _normalise_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip().upper()

    return cleaned or None


def _string_list(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()

    return {
        item.strip().upper()
        for item in value
        if isinstance(item, str) and item.strip()
    }


def _explicit_execution_tag(
    trade: dict[str, Any],
    expected: str,
) -> bool | None:
    tag = _normalise_string(trade.get("executionTag"))

    if tag is None:
        return None

    return tag == expected


def _stop_moved(trade: dict[str, Any]) -> bool | None:
    value = _execution(trade).get("stopMoved")

    if isinstance(value, bool):
        return value

    return None


def _rule_violation(trade: dict[str, Any]) -> bool | None:
    behavior = _behavior(trade)
    rules = _rules(trade)

    behavior_violations = _string_list(behavior.get("ruleViolations"))
    rule_violations = _string_list(rules.get("violated"))

    if behavior_violations or rule_violations:
        return True

    if (
        isinstance(behavior.get("ruleViolations"), list)
        or isinstance(rules.get("violated"), list)
    ):
        return False

    return None


def _counter_structure(trade: dict[str, Any]) -> bool | None:
    tags = _string_list(_fingerprint(trade).get("tags"))

    if "COUNTER_STRUCTURE" in tags:
        return True

    if isinstance(_fingerprint(trade).get("tags"), list):
        return False

    return None


def _behavior_tag(
    trade: dict[str, Any],
    expected: str,
) -> bool | None:
    tags = _string_list(_behavior(trade).get("tags"))

    if not tags and not isinstance(_behavior(trade).get("tags"), list):
        return None

    return expected in tags


def detect_leaks(trade: dict[str, Any]) -> list[dict[str, Any]]:
    """Return explicit leak records for a single trade.

    Missing evidence is preserved as UNKNOWN and does not create a leak.
    """

    trade_id = trade.get("id")
    if not isinstance(trade_id, str) or not trade_id.strip():
        return []

    checks = (
        ("LATE_ENTRY", _explicit_execution_tag(trade, "LATE_ENTRY")),
        ("EARLY_EXIT", _explicit_execution_tag(trade, "EARLY_EXIT")),
        ("STOP_MOVEMENT", _stop_moved(trade)),
        ("RULE_VIOLATION", _rule_violation(trade)),
        ("COUNTER_STRUCTURE", _counter_structure(trade)),
        ("OVERTRADING", _explicit_execution_tag(trade, "OVERTRADED")),
        ("REVENGE_TRADING", _behavior_tag(trade, "REVENGE_TRADING")),
    )

    records: list[dict[str, Any]] = []

    for leak_type, detected in checks:
        if detected is not True:
            continue

        records.append(
            {
                "type": leak_type,
                "tradeId": trade_id,
                "version": LEAK_MAP_VERSION,
                "evidence": "EXPLICIT_CANONICAL",
            }
        )

    return records


def detect_leak_types(trade: dict[str, Any]) -> list[str]:
    """Return detected leak types in stable deterministic order."""

    return [record["type"] for record in detect_leaks(trade)]

LEAK_LABELS = {
    "LATE_ENTRY": "Late entries",
    "EARLY_EXIT": "Early exits",
    "STOP_MOVEMENT": "Stop movement",
    "RULE_VIOLATION": "Rule violations",
    "COUNTER_STRUCTURE": "Counter-structure trades",
    "OVERTRADING": "Overtrading",
    "REVENGE_TRADING": "Revenge trading",
}


def _actual_r(trade: dict[str, Any]) -> float | None:
    entry = trade.get("entry")
    stop = trade.get("stopLoss")
    exit_price = trade.get("exitPrice")
    direction = _normalise_string(trade.get("direction"))

    if not all(isinstance(value, (int, float)) for value in (entry, stop, exit_price)):
        return None

    if direction not in {"LONG", "SHORT"}:
        return None

    risk = abs(float(entry) - float(stop))

    if risk <= 0:
        return None

    profit = (
        float(exit_price) - float(entry)
        if direction == "LONG"
        else float(entry) - float(exit_price)
    )

    return round(profit / risk, 6)


def _evidence_strength(
    occurrence_count: int,
    r_coverage: float,
) -> str:
    if occurrence_count <= 0:
        return "NONE"

    if occurrence_count >= 10 and r_coverage >= 0.8:
        return "STRONG"

    if occurrence_count >= 5 and r_coverage >= 0.5:
        return "MODERATE"

    return "LIMITED"


def build_leak_map(
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate deterministic leak occurrences across historical trades."""

    grouped: dict[str, dict[str, Any]] = {
        leak_type: {
            "type": leak_type,
            "label": LEAK_LABELS[leak_type],
            "occurrenceCount": 0,
            "supportingTradeIds": [],
            "rImpact": None,
            "actualRCoverage": 0.0,
            "evidenceStrength": "NONE",
            "version": LEAK_MAP_VERSION,
        }
        for leak_type in SUPPORTED_LEAK_TYPES
    }

    r_values: dict[str, list[float]] = {
        leak_type: []
        for leak_type in SUPPORTED_LEAK_TYPES
    }

    for trade in trades:
        for leak in detect_leaks(trade):
            leak_type = leak["type"]
            group = grouped[leak_type]
            trade_id = leak["tradeId"]

            group["occurrenceCount"] += 1

            if trade_id not in group["supportingTradeIds"]:
                group["supportingTradeIds"].append(trade_id)

            actual_r = _actual_r(trade)

            if actual_r is not None:
                r_values[leak_type].append(actual_r)

    results = []

    for leak_type in SUPPORTED_LEAK_TYPES:
        group = grouped[leak_type]
        count = group["occurrenceCount"]
        values = r_values[leak_type]

        if count > 0:
            group["actualRCoverage"] = round(len(values) / count, 6)
            group["rImpact"] = (
                round(sum(values), 6)
                if values
                else None
            )
            group["evidenceStrength"] = _evidence_strength(
                count,
                group["actualRCoverage"],
            )

        results.append(group)

    return results


TREND_MIN_OCCURRENCES = 6
TREND_MIN_PERIODS = 3


def calculate_leak_trend(
    occurrences: list[dict[str, Any]],
) -> str:
    """Return a deterministic historical trend state.

    Occurrences must contain a valid ISO-like timestamp under ``timestamp``.
    The current implementation uses monthly buckets.
    """

    if not isinstance(occurrences, list):
        return "INSUFFICIENT_HISTORY"

    dated = []

    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            continue

        timestamp = occurrence.get("timestamp")

        if not isinstance(timestamp, str) or len(timestamp) < 7:
            continue

        period = timestamp[:7]

        if len(period) == 7 and period[4] == "-":
            dated.append(period)

    periods = sorted(dated)

    if len(dated) < TREND_MIN_OCCURRENCES:
        return "INSUFFICIENT_HISTORY"

    distinct_periods = sorted(set(periods))

    if len(distinct_periods) < TREND_MIN_PERIODS:
        return "INSUFFICIENT_HISTORY"

    counts = [
        periods.count(period)
        for period in distinct_periods
    ]

    midpoint = len(counts) // 2

    first_half = counts[:midpoint]
    second_half = counts[midpoint:]

    if not first_half or not second_half:
        return "INSUFFICIENT_HISTORY"

    first_average = sum(first_half) / len(first_half)
    second_average = sum(second_half) / len(second_half)

    if second_average > first_average:
        return "TRENDING_UP"

    if second_average < first_average:
        return "TRENDING_DOWN"

    return "STABLE"

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

"""Deterministic Edge Map analysis for You Can't Trade."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.pattern_discovery import (
    MIN_PATTERN_SAMPLE,
    _actual_r,
)


EDGE_MAP_VERSION = 1


def _regime_value(trade: dict[str, Any]) -> str | None:
    market_context = (trade.get("intelligence") or {}).get("marketContext") or {}
    regime = market_context.get("regime")

    if isinstance(regime, dict):
        regime = regime.get("regime")

    if isinstance(regime, str) and regime.strip():
        return regime.strip()

    return None


def _structure_value(trade: dict[str, Any]) -> str | None:
    market_structure = (
        (trade.get("intelligence") or {}).get("marketStructure") or {}
    )
    structure = market_structure.get("state")

    if isinstance(structure, str) and structure.strip():
        return structure.strip()

    return None


def _dimension_value(
    trade: dict[str, Any],
    dimension: str,
) -> str | None:
    if dimension == "setup":
        value = trade.get("setup")
    elif dimension == "session":
        value = trade.get("session")
    elif dimension == "direction":
        value = trade.get("direction")
    elif dimension == "market_regime":
        value = _regime_value(trade)
    elif dimension == "structure_state":
        value = _structure_value(trade)
    else:
        raise ValueError(f"Unsupported Edge Map dimension: {dimension}")

    return value.strip() if isinstance(value, str) and value.strip() else None


def build_edge_map(
    trades: list[dict[str, Any]],
    dimension_a: str,
    dimension_b: str,
    min_sample: int = MIN_PATTERN_SAMPLE,
) -> list[dict[str, Any]]:
    """Build deterministic two-dimensional performance cells."""

    if min_sample < 1:
        raise ValueError("min_sample must be at least 1.")

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for trade in trades:
        if trade.get("result") not in {"WIN", "LOSS", "BE"}:
            continue

        value_a = _dimension_value(trade, dimension_a)
        value_b = _dimension_value(trade, dimension_b)

        if value_a is None or value_b is None:
            continue

        groups[(value_a, value_b)].append(trade)

    cells: list[dict[str, Any]] = []

    for (value_a, value_b), matches in groups.items():
        if len(matches) < min_sample:
            continue

        wins = sum(trade.get("result") == "WIN" for trade in matches)
        losses = sum(trade.get("result") == "LOSS" for trade in matches)

        actual_r = [
            value
            for trade in matches
            if (value := _actual_r(trade)) is not None
        ]

        average_r = (
            round(sum(actual_r) / len(actual_r), 6)
            if actual_r
            else None
        )

        win_rate = (
            round(wins / (wins + losses), 6)
            if wins + losses
            else None
        )

        cells.append(
            {
                "dimensionA": dimension_a,
                "dimensionB": dimension_b,
                "valueA": value_a,
                "valueB": value_b,
                "sampleSize": len(matches),
                "outcomes": {
                    "wins": wins,
                    "losses": losses,
                    "breakEven": sum(
                        trade.get("result") == "BE"
                        for trade in matches
                    ),
                },
                "winRate": win_rate,
                "averageR": average_r,
                "expectancy": average_r,
                "evidenceStrength": {
                    "sampleSize": len(matches),
                    "actualRCoverage": (
                        round(len(actual_r) / len(matches), 6)
                        if matches
                        else 0.0
                    ),
                    "level": (
                        "LOW"
                        if len(matches) < 10
                        else "OBSERVATIONAL"
                    ),
                    "minimumSample": min_sample,
                },
                "sourceTradeIds": [
                    trade.get("id")
                    for trade in matches
                    if isinstance(trade.get("id"), str)
                ],
                "computationVersion": EDGE_MAP_VERSION,
            }
        )

    return sorted(
        cells,
        key=lambda cell: (
            -cell["sampleSize"],
            cell["valueA"],
            cell["valueB"],
        ),
    )

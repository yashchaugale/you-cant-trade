"""Deterministic journal data-health reporting for You Can't Trade."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


DATA_HEALTH_VERSION = 1


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _has_valid_risk_geometry(trade: dict[str, Any]) -> bool:
    entry = trade.get("entry")
    stop_loss = trade.get("stopLoss")
    take_profit = trade.get("takeProfit")
    direction = trade.get("direction")

    if not all(
        isinstance(value, (int, float))
        for value in (entry, stop_loss, take_profit)
    ):
        return True

    if direction == "LONG":
        return stop_loss < entry < take_profit

    if direction == "SHORT":
        return take_profit < entry < stop_loss

    return True


def assess_data_health(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Assess completeness and analysis readiness without mutating trades."""
    reviewed = [
        trade
        for trade in trades
        if trade.get("result") in {"WIN", "LOSS", "BE"}
    ]

    missing_outcome = sum(
        not _has_value(trade.get("result"))
        for trade in trades
    )
    missing_symbol = sum(
        not _has_value(trade.get("symbol"))
        for trade in trades
    )
    missing_timeframe = sum(
        not _has_value(trade.get("timeframe"))
        for trade in trades
    )
    missing_direction = sum(
        not _has_value(trade.get("direction"))
        for trade in trades
    )
    missing_entry = sum(
        not isinstance(trade.get("entry"), (int, float))
        for trade in trades
    )
    missing_stop_loss = sum(
        not isinstance(trade.get("stopLoss"), (int, float))
        for trade in trades
    )
    missing_take_profit = sum(
        not isinstance(trade.get("takeProfit"), (int, float))
        for trade in trades
    )
    missing_exit_price = sum(
        not isinstance(trade.get("exitPrice"), (int, float))
        for trade in reviewed
    )
    missing_setup = sum(
        not _has_value(trade.get("setup"))
        for trade in trades
    )
    missing_session = sum(
        not _has_value(trade.get("session"))
        for trade in trades
    )

    missing_actual_r = 0
    missing_market_context = 0
    missing_market_structure = 0
    missing_setup_fingerprint = 0

    analysis_ready = 0

    valid_timestamps: list[datetime] = []
    invalid_timestamp_count = 0
    invalid_record_count = 0
    invalid_risk_count = 0

    for trade in trades:
        intelligence = trade.get("intelligence") or {}
        calculated = intelligence.get("calculated") or {}
        calculated_features = calculated.get("features") or {}
        market_context = intelligence.get("marketContext") or {}
        market_structure = intelligence.get("marketStructure") or {}
        fingerprint = intelligence.get("setupFingerprint") or {}

        timestamp = _parse_timestamp(trade.get("timestamp"))

        if timestamp is None:
            invalid_timestamp_count += 1
        else:
            valid_timestamps.append(timestamp)

        if not _has_value(trade.get("id")) or timestamp is None:
            invalid_record_count += 1

        if not _has_valid_risk_geometry(trade):
            invalid_risk_count += 1

        has_actual_r = isinstance(
            calculated_features.get("actualR"),
            (int, float),
        )
        has_market_context = any(
            _has_value(market_context.get(field))
            for field in (
                "trend",
                "regime",
                "volatility",
                "momentum",
                "session",
                "higherTimeframe",
            )
        )
        has_market_structure = any(
            _has_value(market_structure.get(field))
            for field in (
                "state",
                "events",
                "swings",
                "levels",
            )
        )
        has_setup_fingerprint = bool(
            fingerprint.get("features")
            or fingerprint.get("tags")
        )

        if trade in reviewed and not has_actual_r:
            missing_actual_r += 1
        if not has_market_context:
            missing_market_context += 1
        if not has_market_structure:
            missing_market_structure += 1
        if not has_setup_fingerprint:
            missing_setup_fingerprint += 1

        if (
            trade in reviewed
            and has_actual_r
            and has_market_context
            and has_market_structure
            and has_setup_fingerprint
        ):
            analysis_ready += 1

    id_counts = Counter(
        trade.get("id")
        for trade in trades
        if isinstance(trade.get("id"), str) and trade.get("id")
    )
    duplicate_id_count = sum(
        count - 1
        for count in id_counts.values()
        if count > 1
    )

    normalized_timestamps = [
        timestamp.astimezone(timezone.utc).isoformat()
        for timestamp in valid_timestamps
    ]

    return {
        "computationVersion": DATA_HEALTH_VERSION,
        "totalTrades": len(trades),
        "reviewedTrades": len(reviewed),
        "unreviewedTrades": len(trades) - len(reviewed),
        "missing": {
            "outcome": missing_outcome,
            "symbol": missing_symbol,
            "timeframe": missing_timeframe,
            "direction": missing_direction,
            "entry": missing_entry,
            "stopLoss": missing_stop_loss,
            "takeProfit": missing_take_profit,
            "exitPriceReviewed": missing_exit_price,
            "actualRReviewed": missing_actual_r,
            "setup": missing_setup,
            "session": missing_session,
            "marketContext": missing_market_context,
            "marketStructure": missing_market_structure,
            "setupFingerprint": missing_setup_fingerprint,
        },
        "invalid": {
            "risk": invalid_risk_count,
            "timestamp": invalid_timestamp_count,
            "record": invalid_record_count,
        },
        "duplicates": {
            "ids": duplicate_id_count,
        },
        "dateCoverage": {
            "earliest": min(normalized_timestamps)
            if normalized_timestamps
            else None,
            "latest": max(normalized_timestamps)
            if normalized_timestamps
            else None,
            "validTimestampCount": len(valid_timestamps),
        },
        "analysisReadyTrades": analysis_ready,
    }

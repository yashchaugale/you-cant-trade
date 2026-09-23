"""
Deterministic Trading Memory evidence engine.

Memory is descriptive only. This module does not predict, recommend,
infer causality, or use AI-generated evidence.
"""

from __future__ import annotations

MEMORY_VERSION = 1

EVIDENCE_INSUFFICIENT = "INSUFFICIENT"
EVIDENCE_LIMITED = "LIMITED"
EVIDENCE_MODERATE = "MODERATE"
EVIDENCE_STRONG = "STRONG"

VALID_EVIDENCE_STRENGTHS = {
    EVIDENCE_INSUFFICIENT,
    EVIDENCE_LIMITED,
    EVIDENCE_MODERATE,
    EVIDENCE_STRONG,
}


def _number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pattern_evidence_strength(
    sample_size: int,
    actual_r_coverage: float = 0.0,
    observed_months: int = 0,
    periods_with_actual_r: int = 0,
) -> str:
    """
    Map deterministic pattern/edge evidence into Memory evidence levels.

    Rules intentionally preserve the existing Pattern Discovery evidence
    model while translating it into the Memory contract vocabulary.

    < 3 observations:
        INSUFFICIENT

    3-9 observations:
        LIMITED

    10+ observations:
        MODERATE

    STRONG additionally requires:
        10+ observations
        >= 80% Actual R coverage
        >= 3 observed months
        >= 2 periods containing Actual R
    """
    sample = max(0, int(sample_size or 0))
    coverage = max(0.0, min(1.0, _number(actual_r_coverage)))
    months = max(0, int(observed_months or 0))
    periods = max(0, int(periods_with_actual_r or 0))

    if sample < 3:
        return EVIDENCE_INSUFFICIENT

    if sample < 10:
        return EVIDENCE_LIMITED

    if coverage >= 0.8 and months >= 3 and periods >= 2:
        return EVIDENCE_STRONG

    return EVIDENCE_MODERATE


def leak_evidence_strength(
    occurrence_count: int,
    actual_r_coverage: float = 0.0,
) -> str:
    """
    Map deterministic Leak Map evidence into Memory evidence levels.

    Rules preserve the existing Leak Map thresholds:

        >= 10 occurrences and >= 80% R coverage -> STRONG
        >= 5 occurrences and >= 50% R coverage  -> MODERATE
        otherwise with evidence                  -> LIMITED
        zero occurrences                         -> INSUFFICIENT
    """
    count = max(0, int(occurrence_count or 0))
    coverage = max(0.0, min(1.0, _number(actual_r_coverage)))

    if count == 0:
        return EVIDENCE_INSUFFICIENT

    if count >= 10 and coverage >= 0.8:
        return EVIDENCE_STRONG

    if count >= 5 and coverage >= 0.5:
        return EVIDENCE_MODERATE

    return EVIDENCE_LIMITED


def evidence_from_observation(observation: dict) -> str:
    """
    Convert an existing deterministic observation into Memory evidence.

    Supported sources:
      - PATTERN / EDGE
      - LEAK

    Missing or unsupported evidence remains INSUFFICIENT rather than being
    interpreted as failure or disproof.
    """
    if not isinstance(observation, dict):
        return EVIDENCE_INSUFFICIENT

    source = str(
        observation.get("source")
        or observation.get("sourceType")
        or observation.get("kind")
        or ""
    ).upper()

    if source in {"PATTERN", "EDGE", "EDGE_MAP"}:
        return pattern_evidence_strength(
            sample_size=observation.get("sampleSize", 0),
            actual_r_coverage=observation.get(
                "actualRCoverage",
                observation.get("actual_r_coverage", 0.0),
            ),
            observed_months=observation.get("observedMonths", 0),
            periods_with_actual_r=observation.get(
                "periodsWithActualR",
                observation.get("periods_with_actual_r", 0),
            ),
        )

    if source in {"LEAK", "LEAK_MAP"}:
        return leak_evidence_strength(
            occurrence_count=observation.get(
                "occurrenceCount",
                observation.get("sampleSize", 0),
            ),
            actual_r_coverage=observation.get(
                "actualRCoverage",
                observation.get("actual_r_coverage", 0.0),
            ),
        )

    return EVIDENCE_INSUFFICIENT


def build_memory_evidence(observation: dict) -> dict:
    """
    Return the canonical evidence portion of a Memory finding.

    This function is deliberately side-effect free so the same observation
    can be evaluated again during a deterministic recheck.
    """
    evidence_strength = evidence_from_observation(observation)

    source_trade_ids = observation.get(
        "sourceTradeIds",
        observation.get("supportingTradeIds", []),
    )

    if not isinstance(source_trade_ids, list):
        source_trade_ids = []

    source_trade_ids = list(dict.fromkeys(
        trade_id for trade_id in source_trade_ids
        if trade_id is not None and str(trade_id).strip()
    ))

    sample_size = observation.get("sampleSize")

    if sample_size is None:
        sample_size = observation.get(
            "occurrenceCount",
            len(source_trade_ids),
        )

    try:
        sample_size = max(0, int(sample_size))
    except (TypeError, ValueError):
        sample_size = len(source_trade_ids)

    return {
        "sampleSize": sample_size,
        "supportingTradeIds": source_trade_ids,
        "evidenceStrength": evidence_strength,
        "memoryVersion": MEMORY_VERSION,
    }


def _normalise_timestamp(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _first_observed_from_trades(
    observation: dict,
    trade_timestamps: dict[str, str] | None = None,
):
    explicit = _normalise_timestamp(
        observation.get("firstObserved")
        or observation.get("first_observed")
    )
    if explicit:
        return explicit

    timestamps = []
    trade_ids = observation.get(
        "sourceTradeIds",
        observation.get("supportingTradeIds", []),
    )

    if trade_timestamps:
        for trade_id in trade_ids or []:
            timestamp = _normalise_timestamp(trade_timestamps.get(trade_id))
            if timestamp:
                timestamps.append(timestamp)

    return min(timestamps) if timestamps else None


def build_memory_finding(
    observation: dict,
    finding_type: str,
    statement: str,
    trade_timestamps: dict[str, str] | None = None,
    finding_id: str | None = None,
) -> dict:
    """
    Build a deterministic Memory Finding candidate from an observation.

    This is a pure constructor. It does not persist anything and does not
    alter the observation or any canonical Trade Case File.
    """
    if not isinstance(observation, dict):
        raise ValueError("observation must be a dictionary")

    finding_type = str(finding_type or "").strip().upper()
    if finding_type not in {
        "EDGE",
        "LEAK",
        "SETUP",
        "CONTEXT",
        "BEHAVIOR",
        "EXECUTION",
        "EXPERIMENT_RESULT",
    }:
        raise ValueError(f"unsupported memory finding type: {finding_type}")

    statement = str(statement or "").strip()
    if not statement:
        raise ValueError("statement is required")

    evidence = build_memory_evidence(observation)

    first_observed = _first_observed_from_trades(
        observation,
        trade_timestamps=trade_timestamps,
    )

    if not first_observed:
        raise ValueError("firstObserved requires deterministic evidence timestamp")

    if finding_id is None:
        finding_id = str(observation.get("findingId") or "").strip() or None

    if not finding_id:
        raise ValueError("finding_id is required")

    return {
        "id": finding_id,
        "type": finding_type,
        "statement": statement,
        "sampleSize": evidence["sampleSize"],
        "evidenceStrength": evidence["evidenceStrength"],
        "firstObserved": first_observed,
        "lastVerified": None,
        "status": "OBSERVED",
        "contractVersion": MEMORY_VERSION,
        "supportingTradeIds": evidence["supportingTradeIds"],
    }

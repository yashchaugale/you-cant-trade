from services.memory import (
    MEMORY_VERSION,
    EVIDENCE_INSUFFICIENT,
    EVIDENCE_LIMITED,
    EVIDENCE_MODERATE,
    EVIDENCE_STRONG,
    build_memory_evidence,
    evidence_from_observation,
    leak_evidence_strength,
    pattern_evidence_strength,
)


def test_pattern_evidence_preserves_existing_thresholds():
    assert pattern_evidence_strength(2) == EVIDENCE_INSUFFICIENT
    assert pattern_evidence_strength(3) == EVIDENCE_LIMITED
    assert pattern_evidence_strength(9) == EVIDENCE_LIMITED
    assert pattern_evidence_strength(10) == EVIDENCE_MODERATE
    assert pattern_evidence_strength(
        10,
        actual_r_coverage=0.8,
        observed_months=3,
        periods_with_actual_r=2,
    ) == EVIDENCE_STRONG


def test_pattern_strong_requires_all_required_evidence():
    assert pattern_evidence_strength(
        10,
        actual_r_coverage=0.8,
        observed_months=2,
        periods_with_actual_r=2,
    ) == EVIDENCE_MODERATE

    assert pattern_evidence_strength(
        10,
        actual_r_coverage=0.7,
        observed_months=3,
        periods_with_actual_r=2,
    ) == EVIDENCE_MODERATE


def test_leak_evidence_preserves_existing_thresholds():
    assert leak_evidence_strength(0) == EVIDENCE_INSUFFICIENT
    assert leak_evidence_strength(1, 1.0) == EVIDENCE_LIMITED
    assert leak_evidence_strength(5, 0.5) == EVIDENCE_MODERATE
    assert leak_evidence_strength(10, 0.8) == EVIDENCE_STRONG


def test_missing_or_unknown_source_is_insufficient():
    assert evidence_from_observation({}) == EVIDENCE_INSUFFICIENT
    assert evidence_from_observation({"source": "UNKNOWN"}) == EVIDENCE_INSUFFICIENT
    assert evidence_from_observation(None) == EVIDENCE_INSUFFICIENT


def test_build_memory_evidence_is_deterministic_and_deduplicates_trades():
    result = build_memory_evidence({
        "source": "PATTERN",
        "sampleSize": 4,
        "sourceTradeIds": ["t1", "t2", "t1", "", None],
    })

    assert result == {
        "sampleSize": 4,
        "supportingTradeIds": ["t1", "t2"],
        "evidenceStrength": EVIDENCE_LIMITED,
        "memoryVersion": MEMORY_VERSION,
    }


def test_build_memory_evidence_uses_supporting_trade_ids_when_needed():
    result = build_memory_evidence({
        "source": "LEAK",
        "occurrenceCount": 5,
        "actualRCoverage": 0.5,
        "supportingTradeIds": ["t1", "t2", "t3", "t4", "t5"],
    })

    assert result["sampleSize"] == 5
    assert result["supportingTradeIds"] == ["t1", "t2", "t3", "t4", "t5"]
    assert result["evidenceStrength"] == EVIDENCE_MODERATE

from services.memory import (
    MEMORY_VERSION,
    EVIDENCE_INSUFFICIENT,
    EVIDENCE_LIMITED,
    EVIDENCE_MODERATE,
    EVIDENCE_STRONG,
    build_memory_evidence,
    build_memory_finding,
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


def test_build_memory_finding_creates_observed_finding():
    result = build_memory_finding(
        {
            "source": "PATTERN",
            "sampleSize": 4,
            "sourceTradeIds": ["t2", "t1"],
            "firstObserved": "2026-01-02T10:00:00Z",
        },
        finding_type="EDGE",
        statement="This setup occurred repeatedly.",
        finding_id="memory-1",
    )

    assert result == {
        "id": "memory-1",
        "type": "EDGE",
        "statement": "This setup occurred repeatedly.",
        "sampleSize": 4,
        "evidenceStrength": EVIDENCE_LIMITED,
        "firstObserved": "2026-01-02T10:00:00Z",
        "lastVerified": None,
        "status": "OBSERVED",
        "contractVersion": MEMORY_VERSION,
        "supportingTradeIds": ["t2", "t1"],
    }


def test_build_memory_finding_derives_first_observed_from_supporting_trades():
    result = build_memory_finding(
        {
            "source": "PATTERN",
            "sampleSize": 3,
            "sourceTradeIds": ["t2", "t1"],
        },
        finding_type="SETUP",
        statement="The setup appeared in these trades.",
        trade_timestamps={
            "t1": "2026-01-01T10:00:00Z",
            "t2": "2026-01-03T10:00:00Z",
        },
        finding_id="memory-2",
    )

    assert result["firstObserved"] == "2026-01-01T10:00:00Z"


def test_build_memory_finding_rejects_missing_first_observed():
    try:
        build_memory_finding(
            {
                "source": "PATTERN",
                "sampleSize": 3,
                "sourceTradeIds": ["t1"],
            },
            finding_type="EDGE",
            statement="Missing timestamp.",
            finding_id="memory-3",
        )
    except ValueError as exc:
        assert str(exc) == "firstObserved requires deterministic evidence timestamp"
    else:
        raise AssertionError("expected ValueError")


def test_build_memory_finding_rejects_invalid_type():
    try:
        build_memory_finding(
            {
                "source": "PATTERN",
                "sampleSize": 3,
                "sourceTradeIds": ["t1"],
                "firstObserved": "2026-01-01T10:00:00Z",
            },
            finding_type="PREDICTION",
            statement="Invalid.",
            finding_id="memory-4",
        )
    except ValueError as exc:
        assert str(exc) == "unsupported memory finding type: PREDICTION"
    else:
        raise AssertionError("expected ValueError")

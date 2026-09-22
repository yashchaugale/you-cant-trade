from services.leak_map import detect_leaks, detect_leak_types


def test_counter_structure_is_detected_from_canonical_fingerprint():
    trade = {
        "id": "trade-1",
        "intelligence": {
            "setupFingerprint": {
                "tags": ["COUNTER_STRUCTURE"],
            }
        },
    }

    assert detect_leak_types(trade) == ["COUNTER_STRUCTURE"]


def test_missing_evidence_does_not_create_leaks():
    trade = {
        "id": "trade-2",
        "executionTag": None,
        "intelligence": {
            "execution": {
                "stopMoved": None,
            },
            "behavior": {
                "ruleViolations": [],
                "tags": [],
            },
            "rules": {
                "violated": [],
            },
            "setupFingerprint": {
                "tags": [],
            },
        },
    }

    assert detect_leaks(trade) == []


def test_explicit_execution_tags_are_detected():
    trade = {
        "id": "trade-3",
        "executionTag": "LATE_ENTRY",
    }

    assert detect_leak_types(trade) == ["LATE_ENTRY"]


def test_overtrading_execution_tag_is_detected():
    trade = {
        "id": "trade-4",
        "executionTag": "OVERTRADED",
    }

    assert detect_leak_types(trade) == ["OVERTRADING"]


def test_stop_movement_is_detected():
    trade = {
        "id": "trade-5",
        "intelligence": {
            "execution": {
                "stopMoved": True,
            }
        },
    }

    assert detect_leak_types(trade) == ["STOP_MOVEMENT"]


def test_rule_violation_is_detected_from_behavior():
    trade = {
        "id": "trade-6",
        "intelligence": {
            "behavior": {
                "ruleViolations": ["NO_TRADE_AGAINST_STRUCTURE"],
                "tags": [],
            },
        },
    }

    assert detect_leak_types(trade) == ["RULE_VIOLATION"]


def test_rule_violation_is_detected_from_rules():
    trade = {
        "id": "trade-7",
        "intelligence": {
            "rules": {
                "violated": ["RISK_LIMIT"],
            },
        },
    }

    assert detect_leak_types(trade) == ["RULE_VIOLATION"]


def test_revenge_trading_requires_explicit_behavior_tag():
    trade = {
        "id": "trade-8",
        "intelligence": {
            "behavior": {
                "tags": ["REVENGE_TRADING"],
            },
        },
    }

    assert detect_leak_types(trade) == ["REVENGE_TRADING"]


def test_loss_does_not_imply_revenge_trading():
    trade = {
        "id": "trade-9",
        "result": "LOSS",
        "intelligence": {
            "behavior": {
                "tags": [],
            },
        },
    }

    assert detect_leaks(trade) == []


def test_empty_rule_lists_mean_no_recorded_violation():
    trade = {
        "id": "trade-10",
        "intelligence": {
            "behavior": {
                "ruleViolations": [],
            },
            "rules": {
                "violated": [],
            },
        },
    }

    assert detect_leaks(trade) == []


def test_multiple_explicit_leaks_are_returned_in_stable_order():
    trade = {
        "id": "trade-11",
        "executionTag": "LATE_ENTRY",
        "intelligence": {
            "execution": {
                "stopMoved": True,
            },
            "setupFingerprint": {
                "tags": ["COUNTER_STRUCTURE"],
            },
            "behavior": {
                "tags": ["REVENGE_TRADING"],
            },
        },
    }

    assert detect_leak_types(trade) == [
        "LATE_ENTRY",
        "STOP_MOVEMENT",
        "COUNTER_STRUCTURE",
        "REVENGE_TRADING",
    ]


def test_build_leak_map_aggregates_supported_leaks():
    from services.leak_map import build_leak_map

    trades = [
        {
            "id": "trade-a",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 99,
            "exitPrice": 102,
            "executionTag": "LATE_ENTRY",
        },
        {
            "id": "trade-b",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 99,
            "exitPrice": 99.5,
            "intelligence": {
                "setupFingerprint": {
                    "tags": ["COUNTER_STRUCTURE"],
                }
            },
        },
        {
            "id": "trade-c",
            "executionTag": "LATE_ENTRY",
        },
    ]

    result = build_leak_map(trades)

    late_entry = next(item for item in result if item["type"] == "LATE_ENTRY")
    counter_structure = next(
        item for item in result if item["type"] == "COUNTER_STRUCTURE"
    )

    assert late_entry["occurrenceCount"] == 2
    assert late_entry["supportingTradeIds"] == ["trade-a", "trade-c"]
    assert late_entry["actualRCoverage"] == 0.5
    assert late_entry["rImpact"] == 2.0
    assert late_entry["evidenceStrength"] == "LIMITED"

    assert counter_structure["occurrenceCount"] == 1
    assert counter_structure["supportingTradeIds"] == ["trade-b"]
    assert counter_structure["actualRCoverage"] == 1.0
    assert counter_structure["rImpact"] == -0.5


def test_build_leak_map_does_not_turn_missing_evidence_into_occurrences():
    from services.leak_map import build_leak_map

    result = build_leak_map(
        [
            {
                "id": "trade-a",
                "result": "LOSS",
            }
        ]
    )

    assert all(item["occurrenceCount"] == 0 for item in result)

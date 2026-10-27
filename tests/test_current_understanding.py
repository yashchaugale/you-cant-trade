import unittest

from services import current_understanding
from services.current_understanding import build_current_understanding


class CurrentUnderstandingTests(unittest.TestCase):
    def test_no_trades(self):
        result = build_current_understanding(trade_count=0)

        self.assertEqual(result["status"], "NO_TRADES")
        self.assertEqual(result["tradeCount"], 0)
        self.assertIsNone(result["observation"])
        self.assertIsNone(result["watch"])
        self.assertIsNone(result["recentChange"])

    def test_no_qualifying_pattern_returns_learning(self):
        result = build_current_understanding(
            trade_count=2,
            patterns=[
                {
                    "dimension": "setup",
                    "value": "breakout",
                    "sampleSize": 2,
                }
            ],
        )

        self.assertEqual(result["status"], "LEARNING")
        self.assertIsNone(result["observation"])

    def test_selects_pattern_deterministically(self):
        patterns = [
            {
                "dimension": "setup",
                "value": "breakout",
                "sampleSize": 5,
                "actualR": {"average": 0.8},
                "evidenceStrength": {
                    "level": "LOW",
                    "actualRCoverage": 1.0,
                },
                "sourceTradeIds": ["t1", "t2", "t3", "t4", "t5"],
                "computationVersion": 3,
            },
            {
                "dimension": "session",
                "value": "NY",
                "sampleSize": 5,
                "actualR": {"average": 0.4},
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 0.8,
                },
                "sourceTradeIds": ["t6", "t7", "t8", "t9", "t10"],
                "computationVersion": 3,
            },
        ]

        result = build_current_understanding(
            trade_count=10,
            patterns=patterns,
        )

        self.assertEqual(result["status"], "READY")
        self.assertEqual(
            result["observation"]["source"]["dimension"],
            "session",
        )
        self.assertEqual(
            result["observation"]["evidenceStrength"],
            "MODERATE",
        )
        self.assertEqual(result["observation"]["sampleSize"], 5)

    def test_selects_negative_leak_as_watch(self):
        result = build_current_understanding(
            trade_count=10,
            leaks=[
                {
                    "type": "LATE_ENTRY",
                    "label": "Late entries",
                    "occurrenceCount": 6,
                    "rImpact": -4.0,
                    "actualRCoverage": 1.0,
                    "evidenceStrength": "MODERATE",
                    "supportingTradeIds": ["t1", "t2"],
                }
            ],
        )

        self.assertIsNotNone(result["watch"])
        self.assertEqual(result["watch"]["type"], "LEAK")
        self.assertEqual(result["watch"]["sampleSize"], 6)

    def test_formats_recent_change(self):
        result = build_current_understanding(
            trade_count=50,
            compare={
                "version": 1,
                "periods": {
                    "current": {
                        "actualCount": 10,
                        "tradeIds": [f"c{i}" for i in range(10)],
                    },
                    "previous": {
                        "actualCount": 20,
                        "tradeIds": [f"p{i}" for i in range(20)],
                    },
                },
                "performance": {
                    "averageR": {
                        "current": 0.8,
                        "previous": 0.2,
                        "change": 0.6,
                    }
                },
            },
        )

        self.assertIsNotNone(result["recentChange"])
        self.assertEqual(
            result["recentChange"]["supportingTradeIds"],
            [f"c{i}" for i in range(10)] + [f"p{i}" for i in range(20)],
        )


    def test_build_pattern_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_pattern_finding

        selected = {
            "evidence": "MODERATE",
            "sampleSize": 8,
            "averageR": 1.25,
            "pattern": {
                "dimension": "setup",
                "value": "Breakout",
                "winRate": 0.625,
                "difference": {
                    "averageR": 0.75,
                },
                "sourceTradeIds": ["t1", "t2", "t3"],
                "computationVersion": 3,
            },
        }

        finding = _build_pattern_finding(selected)

        self.assertEqual(finding["type"], "NEW_PATTERN")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["confidence"], "MODERATE")
        self.assertEqual(finding["sampleSize"], 8)

        self.assertEqual(
            finding["evidence"]["tradeIds"],
            ["t1", "t2", "t3"],
        )
        self.assertEqual(
            finding["evidence"]["source"],
            "pattern_discovery",
        )
        self.assertEqual(
            finding["source"]["engine"],
            "pattern_discovery",
        )
        self.assertEqual(
            finding["supportingTradeIds"],
            ["t1", "t2", "t3"],
        )


    def test_current_understanding_exposes_pattern_finding(self):
        result = build_current_understanding(
            trade_count=8,
            patterns=[
                {
                    "dimension": "setup",
                    "value": "Breakout",
                    "sampleSize": 8,
                    "actualR": {"average": 1.25},
                    "winRate": 0.625,
                    "difference": {
                        "averageR": 0.75,
                    },
                    "evidenceStrength": {
                        "level": "MODERATE",
                        "actualRCoverage": 1.0,
                    },
                    "sourceTradeIds": ["t1", "t2", "t3"],
                    "computationVersion": 3,
                }
            ],
        )

        self.assertEqual(len(result["findings"]), 1)

        finding = result["findings"][0]

        self.assertEqual(finding["type"], "NEW_PATTERN")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["confidence"], "MODERATE")
        self.assertEqual(finding["sampleSize"], 8)
        self.assertEqual(
            finding["supportingTradeIds"],
            ["t1", "t2", "t3"],
        )
        self.assertEqual(
            finding["evidence"]["source"],
            "pattern_discovery",
        )


    def test_performance_change_requires_minimum_sample_in_both_periods(self):
        from services.current_understanding import _build_performance_change_finding

        compare = {
            "version": 1,
            "periods": {
                "current": {"actualCount": 2, "tradeIds": ["c1", "c2"]},
                "previous": {"actualCount": 10, "tradeIds": [f"p{i}" for i in range(10)]},
            },
            "performance": {
                "averageR": {
                    "current": 5.0,
                    "previous": 0.2,
                    "change": 4.8,
                }
            },
        }

        finding = _build_performance_change_finding(compare)

        self.assertIsNone(finding)


    def test_performance_change_ignores_negligible_average_r_difference(self):
        from services.current_understanding import _build_performance_change_finding

        compare = {
            "version": 1,
            "periods": {
                "current": {"actualCount": 10, "tradeIds": [f"c{i}" for i in range(10)]},
                "previous": {"actualCount": 10, "tradeIds": [f"p{i}" for i in range(10)]},
            },
            "performance": {
                "averageR": {
                    "current": 0.15,
                    "previous": 0.0,
                    "change": 0.15,
                }
            },
        }

        self.assertIsNone(_build_performance_change_finding(compare))


    def test_build_performance_change_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_performance_change_finding

        compare = {
            "version": 1,
            "periods": {
                "current": {
                    "actualCount": 10,
                    "tradeIds": [f"c{i}" for i in range(10)],
                },
                "previous": {
                    "actualCount": 20,
                    "tradeIds": [f"p{i}" for i in range(20)],
                },
            },
            "performance": {
                "averageR": {
                    "current": 0.8,
                    "previous": 0.2,
                    "change": 0.6,
                }
            },
        }

        finding = _build_performance_change_finding(compare)

        self.assertEqual(finding["type"], "PERFORMANCE_CHANGE")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["sampleSize"], 10)
        self.assertEqual(
            finding["evidence"]["tradeIds"],
            [f"c{i}" for i in range(10)] + [f"p{i}" for i in range(20)],
        )
        self.assertEqual(
            finding["evidence"]["source"],
            "compare",
        )
        self.assertEqual(
            finding["source"]["engine"],
            "compare",
        )
        self.assertEqual(
            finding["evidence"]["metrics"]["changeR"],
            0.6,
        )


    def test_pattern_and_performance_findings_can_coexist(self):
        result = build_current_understanding(
            trade_count=40,
            patterns=[
                {
                    "dimension": "setup",
                    "value": "Breakout",
                    "sampleSize": 10,
                    "actualR": {"average": 1.2},
                    "winRate": 0.7,
                    "difference": {},
                    "evidenceStrength": {
                        "level": "MODERATE",
                        "actualRCoverage": 1.0,
                    },
                    "sourceTradeIds": ["t1", "t2"],
                    "computationVersion": 3,
                }
            ],
            compare={
                "version": 1,
                "periods": {
                    "current": {
                        "actualCount": 10,
                        "tradeIds": [f"c{i}" for i in range(10)],
                    },
                    "previous": {
                        "actualCount": 20,
                        "tradeIds": [f"p{i}" for i in range(20)],
                    },
                },
                "performance": {
                    "averageR": {
                        "current": 0.8,
                        "previous": 0.2,
                        "change": 0.6,
                    }
                },
            },
        )

        self.assertEqual(len(result["findings"]), 2)
        self.assertEqual(
            {finding["type"] for finding in result["findings"]},
            {"NEW_PATTERN", "PERFORMANCE_CHANGE"},
        )


    def test_build_behavior_change_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_behavior_change_finding

        compare = {
            "version": 1,
            "distributions": {
                "behavior": {
                    "currentSampleSize": 10,
                    "previousSampleSize": 20,
                    "values": [
                        {
                            "value": "LateEntry",
                            "current": {
                                "count": 6,
                                "percentage": 0.6,
                                "tradeIds": [f"c{i}" for i in range(6)],
                            },
                            "previous": {
                                "count": 4,
                                "percentage": 0.1,
                                "tradeIds": [f"p{i}" for i in range(4)],
                            },
                            "percentagePointChange": 0.5,
                        }
                    ],
                }
            },
        }

        finding = _build_behavior_change_finding(compare)

        self.assertEqual(finding["type"], "BEHAVIOR_CHANGE")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["sampleSize"], 10)
        self.assertEqual(
            finding["evidence"]["tradeIds"],
            [f"c{i}" for i in range(6)]
            + [f"p{i}" for i in range(4)],
        )
        self.assertEqual(
            finding["evidence"]["source"],
            "compare",
        )
        self.assertEqual(
            finding["source"]["dimension"],
            "behavior",
        )
        self.assertEqual(
            finding["evidence"]["metrics"]["percentagePointChange"],
            0.5,
        )


    def test_current_understanding_exposes_weakening_pattern_finding(self):
        from services.current_understanding import build_current_understanding

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 12,
                "actualR": {"average": -0.75},
                "sourceTradeIds": ["t1", "t2", "t3"],
                "stability": {
                    "observedPeriods": 4,
                    "profitablePeriods": 1,
                    "losingPeriods": 3,
                    "neutralPeriods": 0,
                    "periodsWithActualR": 3,
                },
                "evidenceStrength": {
                    "level": "MODERATE",
                },
                "computationVersion": 3,
            }
        ]

        result = build_current_understanding(
            trade_count=12,
            patterns=patterns,
            leaks=[],
            compare={},
        )

        weakening = [
            finding
            for finding in result["findings"]
            if finding["type"] == "WEAKENING_PATTERN"
        ]

        self.assertEqual(len(weakening), 1)
        self.assertEqual(weakening[0]["status"], "SUPPORTED")
        self.assertEqual(weakening[0]["sampleSize"], 12)
        self.assertEqual(
            weakening[0]["evidence"]["tradeIds"],
            ["t1", "t2", "t3"],
        )


    def test_build_interesting_relationship_finding_has_traceable_evidence(self):
        from services.current_understanding import (
            _build_interesting_relationship_finding,
        )

        compare = {
            "version": 1,
            "changes": {
                "largestDistributionIncrease": {
                    "field": "behavior",
                    "value": "Revenge Trading",
                    "percentagePointChange": 25.0,
                    "current": {
                        "count": 8,
                        "percentage": 50.0,
                        "tradeIds": ["t1", "t2", "t3", "t4", "t5", "t8", "t9", "t10"],
                    },
                    "previous": {
                        "count": 4,
                        "percentage": 25.0,
                        "tradeIds": ["t6", "t7", "t11", "t12"],
                    },
                },
                "largestDistributionDecrease": None,
            },
        }

        finding = _build_interesting_relationship_finding(compare)

        self.assertEqual(finding["type"], "INTERESTING_RELATIONSHIP")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["evidence"]["source"], "compare")
        self.assertEqual(
            finding["evidence"]["tradeIds"],
            ["t1", "t2", "t3", "t4", "t5", "t8", "t9", "t10",
             "t6", "t7", "t11", "t12"],
        )
        self.assertEqual(
            finding["evidence"]["metrics"]["percentagePointChange"],
            25.0,
        )

    def test_current_understanding_exposes_interesting_relationship_finding(self):
        from services.current_understanding import build_current_understanding

        compare = {
            "version": 1,
            "changes": {
                "largestDistributionIncrease": {
                    "field": "behavior",
                    "value": "Revenge Trading",
                    "percentagePointChange": 25.0,
                    "current": {
                        "count": 8,
                        "percentage": 50.0,
                        "tradeIds": ["t1", "t2", "t3", "t4", "t5", "t8", "t9", "t10"],
                    },
                    "previous": {
                        "count": 4,
                        "percentage": 25.0,
                        "tradeIds": ["t6", "t7", "t11", "t12"],
                    },
                },
                "largestDistributionDecrease": None,
            },
        }

        result = build_current_understanding(
            trade_count=7,
            patterns=[],
            leaks=[],
            compare=compare,
        )

        relationships = [
            finding
            for finding in result["findings"]
            if finding["type"] == "INTERESTING_RELATIONSHIP"
        ]

        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0]["status"], "SUPPORTED")
        self.assertEqual(
            relationships[0]["evidence"]["metrics"]["percentagePointChange"],
            25.0,
        )

    def test_build_data_gap_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_data_gap_finding

        data_health = {
            "computationVersion": 1,
            "totalTrades": 20,
            "missing": {
                "screenshot": 8,
                "marketContext": 3,
                "setup": 2,
            },
        }

        finding = _build_data_gap_finding(data_health)

        self.assertEqual(finding["type"], "DATA_GAP")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["sampleSize"], 20)
        self.assertEqual(
            finding["evidence"]["source"],
            "data_health",
        )
        self.assertEqual(
            finding["evidence"]["metrics"]["missingCount"],
            8,
        )
        self.assertEqual(
            finding["source"]["engine"],
            "data_health",
        )

    def test_current_understanding_exposes_data_gap_finding(self):
        from services.current_understanding import build_current_understanding

        data_health = {
            "computationVersion": 1,
            "totalTrades": 20,
            "missing": {
                "screenshot": 8,
                "marketContext": 3,
                "setup": 2,
            },
        }

        result = build_current_understanding(
            trade_count=20,
            patterns=[],
            leaks=[],
            compare=None,
            data_health=data_health,
        )

        gaps = [
            finding
            for finding in result["findings"]
            if finding["type"] == "DATA_GAP"
        ]

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["status"], "SUPPORTED")
        self.assertEqual(
            gaps[0]["evidence"]["metrics"]["missingCount"],
            8,
        )
        self.assertEqual(
            gaps[0]["source"]["engine"],
            "data_health",
        )

    def test_prioritize_findings_is_deterministic(self):
        from services.current_understanding import _prioritize_findings

        findings = [
            {
                "id": "BEHAVIOR_CHANGE::LateEntry",
                "type": "BEHAVIOR_CHANGE",
                "sampleSize": 6,
                "priority": None,
            },
            {
                "id": "NEW_PATTERN::setup::Breakout",
                "type": "NEW_PATTERN",
                "sampleSize": 10,
                "priority": None,
            },
            {
                "id": "PERFORMANCE_CHANGE::AVERAGE_R",
                "type": "PERFORMANCE_CHANGE",
                "sampleSize": 10,
                "priority": None,
            },
        ]

        ranked = _prioritize_findings(findings)

        self.assertEqual(
            [finding["type"] for finding in ranked],
            [
                "PERFORMANCE_CHANGE",
                "NEW_PATTERN",
                "BEHAVIOR_CHANGE",
            ],
        )

        self.assertEqual(
            [finding["priority"] for finding in ranked],
            [1, 2, 3],
        )


    def test_prioritize_findings_ranks_every_supported_type(self):
        findings = [
            {"id": "data-gap", "type": "DATA_GAP", "sampleSize": 20},
            {"id": "relationship", "type": "INTERESTING_RELATIONSHIP", "sampleSize": 20},
            {"id": "behavior", "type": "BEHAVIOR_CHANGE", "sampleSize": 20},
            {"id": "pattern", "type": "NEW_PATTERN", "sampleSize": 20},
            {"id": "weakening", "type": "WEAKENING_PATTERN", "sampleSize": 20},
            {"id": "performance", "type": "PERFORMANCE_CHANGE", "sampleSize": 20},
        ]

        ranked = current_understanding._prioritize_findings(findings)

        self.assertEqual(
            [finding["type"] for finding in ranked],
            [
                "PERFORMANCE_CHANGE",
                "WEAKENING_PATTERN",
                "NEW_PATTERN",
                "BEHAVIOR_CHANGE",
                "INTERESTING_RELATIONSHIP",
                "DATA_GAP",
            ],
        )


    def test_same_pattern_is_not_surfaced_as_new_and_weakening(self):
        result = build_current_understanding(
            trade_count=12,
            patterns=[
                {
                    "dimension": "setup",
                    "value": "Breakout",
                    "sampleSize": 12,
                    "actualR": {"average": -0.5},
                    "evidenceStrength": {
                        "level": "MODERATE",
                        "actualRCoverage": 1.0,
                    },
                    "stability": {
                        "profitablePeriods": 1,
                        "losingPeriods": 2,
                        "observedPeriods": 3,
                        "periodsWithActualR": 3,
                    },
                    "sourceTradeIds": [f"t{i}" for i in range(12)],
                    "computationVersion": 3,
                }
            ],
        )

        finding_types = [finding["type"] for finding in result["findings"]]

        self.assertFalse(
            "NEW_PATTERN" in finding_types
            and "WEAKENING_PATTERN" in finding_types
        )


    def test_verify_findings_rejects_malformed_finding_collections(self):
        from services.current_understanding import _verify_findings

        self.assertEqual(_verify_findings([None, "invalid", 42]), [])

    def test_verify_findings_rejects_duplicate_trade_ids(self):
        from services.current_understanding import _verify_findings

        finding = {
            "id": "duplicate-trades",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t1", "t2"],
                "source": "pattern_discovery",
            },
        }

        self.assertEqual(_verify_findings([finding]), [])

    def test_verify_findings_rejects_non_finite_metric_values(self):
        from services.current_understanding import _verify_findings

        finding = {
            "id": "non-finite-metric",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": float("nan")},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        self.assertEqual(_verify_findings([finding]), [])

    def test_verify_findings_rejects_invalid_evidence(self):
        findings = [
            {
                "id": "valid",
                "type": "NEW_PATTERN",
                "sampleSize": 3,
                "evidence": {
                    "sampleSize": 3,
                    "metrics": {"averageR": 1.0},
                    "tradeIds": ["t1", "t2", "t3"],
                    "source": "pattern_discovery",
                },
            },
            {
                "id": "missing-source",
                "type": "NEW_PATTERN",
                "evidence": {
                    "sampleSize": 3,
                    "metrics": {"averageR": 1.0},
                    "tradeIds": ["t1", "t2", "t3"],
                },
            },
            {
                "id": "zero-sample",
                "type": "NEW_PATTERN",
                "evidence": {
                    "sampleSize": 0,
                    "metrics": {"averageR": 1.0},
                    "tradeIds": [],
                    "source": "compare",
                },
            },
        ]

        verified = current_understanding._verify_findings(findings)

        self.assertEqual([finding["id"] for finding in verified], ["valid"])

    def test_verify_findings_rejects_float_top_level_sample_size(self):
        finding = {
            "id": "float-top-level-sample",
            "type": "NEW_PATTERN",
            "sampleSize": 3.0,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_fractional_sample_size(self):
        finding = {
            "id": "fractional-sample",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3.7,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_invalid_trade_ids(self):
        finding = {
            "id": "invalid-trade-ids",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "", None],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_mismatched_source(self):
        finding = {
            "id": "wrong-source",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "compare",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_unknown_type(self):
        finding = {
            "id": "unknown-type",
            "type": "MADE_UP_FINDING",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_missing_id(self):
        finding = {
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_missing_type(self):
        finding = {
            "id": "missing-type",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_rejects_mismatched_sample_sizes(self):
        finding = {
            "id": "mismatched-sample",
            "type": "NEW_PATTERN",
            "sampleSize": 10,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual(verified, [])


    def test_verify_findings_accepts_matching_pattern_sample_sizes(self):
        finding = {
            "id": "matching-sample",
            "type": "NEW_PATTERN",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        verified = current_understanding._verify_findings([finding])

        self.assertEqual([item["id"] for item in verified], ["matching-sample"])


    def test_build_weakening_pattern_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_weakening_pattern_finding

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 12,
                "actualR": {"average": -0.75},
                "sourceTradeIds": ["t1", "t2", "t3"],
                "stability": {
                    "observedPeriods": 4,
                    "profitablePeriods": 1,
                    "losingPeriods": 3,
                    "neutralPeriods": 0,
                    "periodsWithActualR": 3,
                },
                "evidenceStrength": {
                    "level": "MODERATE",
                },
                "computationVersion": 3,
            }
        ]

        finding = _build_weakening_pattern_finding(patterns)

        self.assertEqual(finding["type"], "WEAKENING_PATTERN")
        self.assertEqual(finding["status"], "SUPPORTED")
        self.assertEqual(finding["sampleSize"], 12)
        self.assertEqual(
            finding["evidence"]["tradeIds"],
            ["t1", "t2", "t3"],
        )
        self.assertEqual(
            finding["evidence"]["source"],
            "pattern_discovery",
        )
        self.assertEqual(
            finding["source"]["engine"],
            "pattern_discovery",
        )
        self.assertEqual(
            finding["evidence"]["metrics"]["losingPeriods"],
            3,
        )


if __name__ == "__main__":
    unittest.main()


class PatternCandidateValidationTests(unittest.TestCase):
    def test_pattern_candidates_reject_malformed_numeric_values(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {"sampleSize": 3.5, "evidenceStrength": {"level": "MODERATE"}},
            {"sampleSize": True, "evidenceStrength": {"level": "MODERATE"}},
            {"sampleSize": 5, "evidenceStrength": {"level": "MODERATE", "actualRCoverage": float("nan")}},
            {"sampleSize": 5, "evidenceStrength": {"level": "MODERATE", "actualRCoverage": float("inf")}},
            {"sampleSize": 5, "evidenceStrength": {"level": "MODERATE"}, "actualR": {"average": float("nan")}},
            {"sampleSize": 5, "evidenceStrength": {"level": "MODERATE"}, "actualR": {"average": float("inf")}},
            {"sampleSize": 5, "evidenceStrength": {"level": "MODERATE"}, "actualR": {"average": "invalid"}},
        ]

        self.assertEqual(_pattern_candidates(patterns), [])

    def test_pattern_candidates_accept_valid_numeric_evidence(self):
        from services.current_understanding import _pattern_candidates

        candidates = _pattern_candidates([
            {
                "sampleSize": 5,
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 0.8,
                },
                "actualR": {"average": 0.4},
            }
        ])

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["sampleSize"], 5)
        self.assertEqual(candidates[0]["actualRCoverage"], 0.8)
        self.assertEqual(candidates[0]["averageR"], 0.4)

class WatchCandidateValidationTests(unittest.TestCase):
    def test_select_watch_rejects_malformed_numeric_values(self):
        from services.current_understanding import _select_watch

        leaks = [
            {"occurrenceCount": 2.5, "rImpact": -1.0},
            {"occurrenceCount": True, "rImpact": -1.0},
            {"occurrenceCount": 2, "rImpact": float("nan")},
            {"occurrenceCount": 2, "rImpact": float("inf")},
            {"occurrenceCount": 2, "rImpact": -1.0, "actualRCoverage": float("nan")},
            {"occurrenceCount": 2, "rImpact": -1.0, "actualRCoverage": float("inf")},
            {"occurrenceCount": 2, "rImpact": -1.0, "actualRCoverage": -0.1},
        ]

        self.assertIsNone(_select_watch(leaks))

    def test_select_watch_accepts_valid_negative_r_impact(self):
        from services.current_understanding import _select_watch

        selected = _select_watch([
            {
                "type": "LATE_ENTRY",
                "occurrenceCount": 4,
                "rImpact": -1.5,
                "actualRCoverage": 0.8,
                "evidenceStrength": "MODERATE",
            }
        ])

        self.assertIsNotNone(selected)
        self.assertEqual(selected["occurrenceCount"], 4)
        self.assertEqual(selected["rImpact"], -1.5)


class TradeCountValidationTests(unittest.TestCase):
    def test_trade_count_rejects_invalid_values(self):
        for value in (True, 1.5, "invalid", float("nan"), float("inf")):
            with self.subTest(trade_count=value):
                with self.assertRaises((TypeError, ValueError)):
                    build_current_understanding(trade_count=value)

    def test_trade_count_accepts_zero_and_positive_integers(self):
        self.assertEqual(
            build_current_understanding(trade_count=0)["status"],
            "NO_TRADES",
        )
        self.assertEqual(
            build_current_understanding(trade_count=3)["tradeCount"],
            3,
        )


class SurfacedFindingLimitTests(unittest.TestCase):
    def test_current_understanding_surfaces_at_most_three_findings(self):
        from unittest.mock import patch

        findings = [
            {"id": "gap", "type": "DATA_GAP", "sampleSize": 20},
            {"id": "relationship", "type": "INTERESTING_RELATIONSHIP", "sampleSize": 20},
            {"id": "behavior", "type": "BEHAVIOR_CHANGE", "sampleSize": 20},
            {"id": "pattern", "type": "NEW_PATTERN", "sampleSize": 20},
            {"id": "weakening", "type": "WEAKENING_PATTERN", "sampleSize": 20},
            {"id": "performance", "type": "PERFORMANCE_CHANGE", "sampleSize": 20},
        ]

        with patch(
            "services.current_understanding._verify_findings",
            return_value=findings,
        ):
            result = build_current_understanding(trade_count=40)

        self.assertEqual(len(result["findings"]), 3)
        self.assertEqual(
            [finding["type"] for finding in result["findings"]],
            [
                "PERFORMANCE_CHANGE",
                "WEAKENING_PATTERN",
                "NEW_PATTERN",
            ],
        )


class FormatChangeFiniteValueTests(unittest.TestCase):
    def test_format_change_rejects_non_finite_numeric_evidence(self):
        import math
        from services.current_understanding import _format_change

        valid = {
            "periods": {
                "current": {"actualCount": 10, "tradeIds": ["c1"]},
                "previous": {"actualCount": 10, "tradeIds": ["p1"]},
            },
            "performance": {
                "averageR": {"current": 0.8, "previous": 0.2, "change": 0.6}
            },
        }

        for field in ("current", "previous", "change"):
            for invalid in (math.nan, math.inf, -math.inf):
                with self.subTest(field=field, invalid=invalid):
                    compare = {
                        **valid,
                        "performance": {
                            "averageR": {
                                **valid["performance"]["averageR"],
                                field: invalid,
                            }
                        },
                    }
                    self.assertIsNone(_format_change(compare))


class FormatChangeStructureTests(unittest.TestCase):
    def test_format_change_rejects_malformed_nested_structures(self):
        from services.current_understanding import _format_change

        malformed_inputs = [
            {"performance": "invalid"},
            {"performance": {"averageR": []}},
            {"periods": []},
            {"periods": {"current": "invalid"}},
            {"periods": {"previous": []}},
        ]

        for override in malformed_inputs:
            with self.subTest(override=override):
                compare = {
                    "performance": {
                        "averageR": {
                            "current": 0.8,
                            "previous": 0.2,
                            "change": 0.6,
                        }
                    },
                    "periods": {
                        "current": {"actualCount": 10, "tradeIds": ["c1"]},
                        "previous": {"actualCount": 10, "tradeIds": ["p1"]},
                    },
                }
                compare.update(override)
                self.assertIsNone(_format_change(compare))


class FormatChangeTradeIdTests(unittest.TestCase):
    def test_format_change_rejects_invalid_trade_id_evidence(self):
        from services.current_understanding import _format_change

        def make_compare(current_ids, previous_ids, current_count=10, previous_count=10):
            return {
                "performance": {
                    "averageR": {"current": 0.8, "previous": 0.2, "change": 0.6}
                },
                "periods": {
                    "current": {"actualCount": current_count, "tradeIds": current_ids},
                    "previous": {"actualCount": previous_count, "tradeIds": previous_ids},
                },
            }

        invalid_cases = [
            make_compare("not-a-list", [f"p{i}" for i in range(10)]),
            make_compare([f"c{i}" for i in range(10)], "not-a-list"),
            make_compare([""] + [f"c{i}" for i in range(9)], [f"p{i}" for i in range(10)]),
            make_compare(["c1"] * 10, [f"p{i}" for i in range(10)]),
            make_compare([f"c{i}" for i in range(9)], [f"p{i}" for i in range(10)]),
            make_compare([f"t{i}" for i in range(10)], [f"t{i}" for i in range(10)]),
        ]

        for compare in invalid_cases:
            with self.subTest(compare=compare):
                self.assertIsNone(_format_change(compare))


class FormatChangeConsistencyTests(unittest.TestCase):
    def test_format_change_rejects_inconsistent_change_metric(self):
        from services.current_understanding import _format_change

        compare = {
            "performance": {
                "averageR": {
                    "current": 0.8,
                    "previous": 0.2,
                    "change": 1.5,
                }
            },
            "periods": {
                "current": {
                    "actualCount": 10,
                    "tradeIds": [f"c{i}" for i in range(10)],
                },
                "previous": {
                    "actualCount": 10,
                    "tradeIds": [f"p{i}" for i in range(10)],
                },
            },
        }

        self.assertIsNone(_format_change(compare))


class PatternWinRateValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_malformed_win_rate(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": "invalid",
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 1.0,
                },
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class PatternTradeIdValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_malformed_source_trade_ids(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": 0.625,
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 1.0,
                },
                "sourceTradeIds": ["t1", "", "t3"],
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class PatternDifferenceValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_malformed_difference(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": 0.625,
                "difference": "invalid",
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 1.0,
                },
                "sourceTradeIds": ["t1", "t2", "t3"],
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class PatternDifferenceMetricValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_non_numeric_difference_metric(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": 0.625,
                "difference": {
                    "winRate": 0.1,
                    "averageR": "invalid",
                    "expectancy": None,
                },
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 1.0,
                },
                "sourceTradeIds": ["t1", "t2", "t3"],
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class PatternIdentityValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_non_string_identity_fields(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": {"unexpected": "object"},
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": 0.625,
                "evidenceStrength": {
                    "level": "MODERATE",
                    "actualRCoverage": 1.0,
                },
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class PatternEvidenceLevelValidationTests(unittest.TestCase):
    def test_pattern_candidates_rejects_unknown_evidence_level(self):
        from services.current_understanding import _pattern_candidates

        patterns = [
            {
                "dimension": "setup",
                "value": "Breakout",
                "sampleSize": 8,
                "actualR": {"average": 1.25},
                "winRate": 0.625,
                "evidenceStrength": {
                    "level": "SUPER_STRONG",
                    "actualRCoverage": 1.0,
                },
            }
        ]

        self.assertEqual(_pattern_candidates(patterns), [])


class FindingStatusValidationTests(unittest.TestCase):
    def test_verify_findings_rejects_invalid_status(self):
        from services.current_understanding import _verify_findings

        finding = {
            "id": "invalid-status",
            "type": "NEW_PATTERN",
            "status": "PREDICTED",
            "sampleSize": 3,
            "evidence": {
                "sampleSize": 3,
                "metrics": {"averageR": 1.0},
                "tradeIds": ["t1", "t2", "t3"],
                "source": "pattern_discovery",
            },
        }

        self.assertEqual(_verify_findings([finding]), [])


class WatchEvidenceValidationTests(unittest.TestCase):
    def test_select_watch_rejects_invalid_evidence_strength(self):
        from services.current_understanding import _select_watch

        invalid_values = [[], {}, 123, "UNKNOWN"]

        for evidence_strength in invalid_values:
            with self.subTest(evidence_strength=evidence_strength):
                selected = _select_watch([
                    {
                        "type": "LATE_ENTRY",
                        "occurrenceCount": 4,
                        "rImpact": -1.5,
                        "actualRCoverage": 0.8,
                        "evidenceStrength": evidence_strength,
                    }
                ])
                self.assertIsNone(selected)


class DuplicateFindingIdValidationTests(unittest.TestCase):
    def test_verify_findings_rejects_duplicate_finding_ids(self):
        from services.current_understanding import _verify_findings

        def make_finding(finding_id):
            return {
                "id": finding_id,
                "type": "NEW_PATTERN",
                "sampleSize": 3,
                "evidence": {
                    "sampleSize": 3,
                    "metrics": {"averageR": 1.0},
                    "tradeIds": ["t1", "t2", "t3"],
                    "source": "pattern_discovery",
                },
            }

        findings = [
            make_finding("duplicate-id"),
            make_finding("duplicate-id"),
        ]

        verified = _verify_findings(findings)

        self.assertEqual(verified, [])


class FindingMetricTypeValidationTests(unittest.TestCase):
    def test_verify_findings_rejects_non_numeric_metric_values(self):
        from services.current_understanding import _verify_findings

        for invalid_metric in ("not-a-number", [], {"unexpected": "value"}):
            with self.subTest(invalid_metric=invalid_metric):
                finding = {
                    "id": "invalid-metric-type",
                    "type": "NEW_PATTERN",
                    "sampleSize": 3,
                    "evidence": {
                        "sampleSize": 3,
                        "metrics": {"averageR": invalid_metric},
                        "tradeIds": ["t1", "t2", "t3"],
                        "source": "pattern_discovery",
                    },
                }

                self.assertEqual(_verify_findings([finding]), [])

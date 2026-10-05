import unittest

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
                        "tradeIds": ["c1"],
                    },
                    "previous": {
                        "actualCount": 20,
                        "tradeIds": ["p1"],
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
            ["c1", "p1"],
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


    def test_build_performance_change_finding_has_traceable_evidence(self):
        from services.current_understanding import _build_performance_change_finding

        compare = {
            "version": 1,
            "periods": {
                "current": {
                    "actualCount": 10,
                    "tradeIds": ["c1", "c2"],
                },
                "previous": {
                    "actualCount": 20,
                    "tradeIds": ["p1", "p2"],
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
            ["c1", "c2", "p1", "p2"],
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
                        "tradeIds": ["c1"],
                    },
                    "previous": {
                        "actualCount": 20,
                        "tradeIds": ["p1"],
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
                                "tradeIds": ["c1", "c2"],
                            },
                            "previous": {
                                "count": 2,
                                "percentage": 0.1,
                                "tradeIds": ["p1"],
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
        self.assertEqual(finding["sampleSize"], 6)
        self.assertEqual(
            finding["evidence"]["tradeIds"],
            ["c1", "c2", "p1"],
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


if __name__ == "__main__":
    unittest.main()

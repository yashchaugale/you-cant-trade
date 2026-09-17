import unittest

from services.pattern_discovery import discover_patterns


class PatternDiscoveryTests(unittest.TestCase):
    def test_discovers_deterministic_pattern_from_canonical_trade_data(self):
        trades = [
            {
                "id": "trade-1",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "direction": "LONG",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                    "marketStructure": {"state": "BULLISH"},
                    "setupFingerprint": {
                        "features": ["LONG", "TRENDING"],
                        "tags": ["STRUCTURE_ALIGNED"],
                    },
                    "calculated": {
                        "features": {"actualR": 2.0},
                    },
                },
            },
            {
                "id": "trade-2",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "direction": "LONG",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                    "marketStructure": {"state": "BULLISH"},
                    "setupFingerprint": {
                        "features": ["LONG", "TRENDING"],
                        "tags": ["STRUCTURE_ALIGNED"],
                    },
                    "calculated": {
                        "features": {"actualR": 1.0},
                    },
                },
            },
            {
                "id": "trade-3",
                "timestamp": "2026-08-03T10:00:00.000Z",
                "direction": "LONG",
                "setup": "breakout",
                "session": "LONDON",
                "result": "LOSS",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                    "marketStructure": {"state": "BULLISH"},
                    "setupFingerprint": {
                        "features": ["LONG", "TRENDING"],
                        "tags": ["STRUCTURE_ALIGNED"],
                    },
                    "calculated": {
                        "features": {"actualR": -1.0},
                    },
                },
            },
            {
                "id": "unreviewed",
                "timestamp": "2026-08-04T10:00:00.000Z",
                "direction": "LONG",
                "setup": "breakout",
                "result": None,
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        setup = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(setup["sampleSize"], 3)
        self.assertEqual(setup["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })
        self.assertEqual(setup["winRate"], 0.666667)
        self.assertEqual(setup["actualR"]["count"], 3)
        self.assertEqual(setup["actualR"]["total"], 2.0)
        self.assertEqual(setup["actualR"]["average"], 0.666667)
        self.assertEqual(setup["expectancy"], 0.666667)
        self.assertEqual(setup["baseline"]["expectancy"], 0.666667)
        self.assertEqual(setup["difference"]["expectancy"], 0.0)
        self.assertEqual(
            setup["sourceTradeIds"],
            ["trade-1", "trade-2", "trade-3"],
        )
        self.assertEqual(setup["firstObserved"], "2026-08-01T10:00:00.000Z")
        self.assertEqual(setup["lastObserved"], "2026-08-03T10:00:00.000Z")
        self.assertEqual(setup["computationVersion"], 3)
        self.assertEqual(setup["evidenceStrength"]["sampleSize"], 3)
        self.assertEqual(setup["evidenceStrength"]["actualRCoverage"], 1.0)
        self.assertEqual(setup["evidenceStrength"]["observedPeriods"], 1)
        self.assertEqual(setup["evidenceStrength"]["periodsWithActualR"], 1)
        self.assertTrue(setup["evidenceStrength"]["recent"])
        self.assertEqual(setup["evidenceStrength"]["level"], "LOW")
        self.assertEqual(setup["evidenceStrength"]["minimumSample"], 3)
        self.assertEqual(setup["reliability"]["level"], "LOW")

    def test_finding_uses_journal_baseline_and_excludes_break_even_from_win_rate(self):
        trades = [
            {
                "id": "baseline-win-1",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {"actualR": 2.0}},
                },
            },
            {
                "id": "baseline-loss-1",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "setup": "other",
                "result": "LOSS",
                "intelligence": {
                    "calculated": {"features": {"actualR": -1.0}},
                },
            },
            {
                "id": "baseline-be",
                "timestamp": "2026-08-03T10:00:00.000Z",
                "setup": "other",
                "result": "BE",
                "intelligence": {
                    "calculated": {"features": {"actualR": 0.0}},
                },
            },
            {
                "id": "baseline-win-2",
                "timestamp": "2026-08-04T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {"actualR": 1.0}},
                },
            },
            {
                "id": "baseline-loss-2",
                "timestamp": "2026-08-05T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
                "intelligence": {
                    "calculated": {"features": {"actualR": -1.0}},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(breakout["sampleSize"], 3)
        self.assertEqual(breakout["winRate"], 0.666667)
        self.assertEqual(breakout["actualR"]["average"], 0.666667)

        self.assertEqual(breakout["baseline"]["sampleSize"], 5)
        self.assertEqual(breakout["baseline"]["winRate"], 0.5)
        self.assertEqual(breakout["baseline"]["actualR"]["count"], 5)
        self.assertEqual(breakout["baseline"]["actualR"]["average"], 0.2)
        self.assertEqual(
            breakout["baseline"]["tradeIds"],
            [
                "baseline-win-1",
                "baseline-loss-1",
                "baseline-be",
                "baseline-win-2",
                "baseline-loss-2",
            ],
        )
        self.assertEqual(
            breakout["baseline"]["actualR"]["tradeIds"],
            [
                "baseline-win-1",
                "baseline-loss-1",
                "baseline-be",
                "baseline-win-2",
                "baseline-loss-2",
            ],
        )

        self.assertEqual(breakout["difference"]["winRate"], 0.166667)
        self.assertEqual(breakout["difference"]["averageR"], 0.466667)

    def test_baseline_actual_r_excludes_missing_actual_r_without_reducing_sample(self):
        trades = [
            {
                "id": "baseline-win",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {"actualR": 2.0}},
                },
            },
            {
                "id": "baseline-loss",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
                "intelligence": {
                    "calculated": {"features": {"actualR": -1.0}},
                },
            },
            {
                "id": "baseline-be",
                "timestamp": "2026-08-03T10:00:00.000Z",
                "setup": "breakout",
                "result": "BE",
                "intelligence": {
                    "calculated": {"features": {}},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(breakout["baseline"]["sampleSize"], 3)
        self.assertEqual(breakout["baseline"]["winRate"], 0.5)
        self.assertEqual(breakout["baseline"]["actualR"]["count"], 2)
        self.assertEqual(breakout["baseline"]["actualR"]["average"], 0.5)

    def test_pattern_win_rate_excludes_break_even_from_denominator(self):
        trades = [
            {
                "id": "win-1",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "loss-1",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
            },
            {
                "id": "be-1",
                "timestamp": "2026-08-03T10:00:00.000Z",
                "setup": "breakout",
                "result": "BE",
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(breakout["winRate"], 0.5)
        self.assertEqual(breakout["baseline"]["winRate"], 0.5)


    def test_finding_reports_recency_relative_to_latest_journal_trade(self):
        trades = [
            {
                "id": "old-1",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "old-2",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
            },
            {
                "id": "old-3",
                "timestamp": "2026-08-03T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "latest",
                "timestamp": "2026-08-05T10:00:00.000Z",
                "setup": "other",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(breakout["firstObserved"], "2026-08-01T10:00:00.000Z")
        self.assertEqual(breakout["lastObserved"], "2026-08-03T10:00:00.000Z")
        self.assertEqual(
            breakout["recency"],
            {
                "lastObserved": "2026-08-03T10:00:00.000Z",
                "journalLatestObserved": "2026-08-05T10:00:00.000Z",
                "ageInDays": 2,
            },
        )

    def test_finding_recency_is_unknown_when_supporting_timestamps_are_missing(self):
        trades = [
            {
                "id": "missing-time-1",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "missing-time-2",
                "setup": "breakout",
                "result": "LOSS",
            },
            {
                "id": "missing-time-3",
                "setup": "breakout",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(breakout["firstObserved"], None)
        self.assertEqual(breakout["lastObserved"], None)
        self.assertEqual(
            breakout["recency"],
            {
                "lastObserved": None,
                "journalLatestObserved": None,
                "ageInDays": None,
            },
        )

    def test_finding_reports_stability_across_utc_calendar_months(self):
        trades = [
            {
                "id": "jan-win",
                "timestamp": "2026-01-10T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {"actualR": 2.0}},
                },
            },
            {
                "id": "jan-loss",
                "timestamp": "2026-01-20T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
                "intelligence": {
                    "calculated": {"features": {"actualR": -1.0}},
                },
            },
            {
                "id": "feb-loss",
                "timestamp": "2026-02-10T10:00:00.000Z",
                "setup": "breakout",
                "result": "LOSS",
                "intelligence": {
                    "calculated": {"features": {"actualR": -2.0}},
                },
            },
            {
                "id": "feb-win",
                "timestamp": "2026-02-20T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {"actualR": 1.0}},
                },
            },
            {
                "id": "mar-missing-r",
                "timestamp": "2026-03-10T10:00:00.000Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "calculated": {"features": {}},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=5)

        breakout = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup"
            and finding["value"] == "breakout"
        )

        self.assertEqual(
            breakout["stability"],
            {
                "observedPeriods": 3,
                "profitablePeriods": 1,
                "losingPeriods": 1,
                "neutralPeriods": 0,
                "periodsWithActualR": 2,
            },
        )

    def test_finding_discovers_day_from_utc_timestamp(self):
        trades = [
            {
                "id": "saturday-1",
                "timestamp": "2026-08-01T20:00:00-02:00",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "sunday-1",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "other",
                "result": "LOSS",
            },
            {
                "id": "saturday-2",
                "timestamp": "2026-08-08T10:00:00Z",
                "setup": "other",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        saturday = next(
            finding
            for finding in findings
            if finding["dimension"] == "day"
            and finding["value"] == "Saturday"
        )

        self.assertEqual(saturday["sampleSize"], 2)
        self.assertEqual(
            saturday["sourceTradeIds"],
            ["saturday-1", "saturday-2"],
        )

    def test_finding_discovers_time_from_utc_timestamp(self):
        trades = [
            {
                "id": "time-1",
                "timestamp": "2026-08-01T20:30:00-02:00",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "time-2",
                "timestamp": "2026-08-02T22:15:00Z",
                "setup": "other",
                "result": "LOSS",
            },
            {
                "id": "time-3",
                "timestamp": "2026-08-08T22:45:00Z",
                "setup": "other",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        time_pattern = next(
            finding
            for finding in findings
            if finding["dimension"] == "time"
            and finding["value"] == "22:00"
        )

        self.assertEqual(time_pattern["sampleSize"], 3)
        self.assertEqual(
            time_pattern["sourceTradeIds"],
            ["time-1", "time-2", "time-3"],
        )

    def test_time_pattern_ignores_missing_and_invalid_timestamps(self):
        trades = [
            {
                "id": "valid-time-1",
                "timestamp": "2026-08-01T22:00:00Z",
                "result": "WIN",
            },
            {
                "id": "valid-time-2",
                "timestamp": "2026-08-08T22:59:00Z",
                "result": "LOSS",
            },
            {
                "id": "missing-time",
                "result": "WIN",
            },
            {
                "id": "invalid-time",
                "timestamp": "not-a-timestamp",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        time_pattern = next(
            finding
            for finding in findings
            if finding["dimension"] == "time"
            and finding["value"] == "22:00"
        )

        self.assertEqual(time_pattern["sampleSize"], 2)
        self.assertEqual(
            time_pattern["sourceTradeIds"],
            ["valid-time-1", "valid-time-2"],
        )

    def test_day_pattern_ignores_missing_and_invalid_timestamps(self):
        trades = [
            {
                "id": "valid-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "result": "WIN",
            },
            {
                "id": "valid-2",
                "timestamp": "2026-08-08T10:00:00Z",
                "result": "LOSS",
            },
            {
                "id": "missing-time",
                "result": "WIN",
            },
            {
                "id": "invalid-time",
                "timestamp": "not-a-timestamp",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        saturday = next(
            finding
            for finding in findings
            if finding["dimension"] == "day"
            and finding["value"] == "Saturday"
        )

        self.assertEqual(saturday["sampleSize"], 2)
        self.assertEqual(
            saturday["sourceTradeIds"],
            ["valid-1", "valid-2"],
        )

    def test_finding_discovers_setup_session_combination(self):
        trades = [
            {
                "id": "setup-session-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "setup-session-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "LOSS",
            },
            {
                "id": "setup-session-3",
                "timestamp": "2026-08-03T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "other-session",
                "timestamp": "2026-08-04T10:00:00Z",
                "setup": "breakout",
                "session": "NEW_YORK",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        combination = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup_session"
            and finding["value"] == "breakout + LONDON"
        )

        self.assertEqual(combination["sampleSize"], 3)
        self.assertEqual(
            combination["sourceTradeIds"],
            [
                "setup-session-1",
                "setup-session-2",
                "setup-session-3",
            ],
        )
        self.assertEqual(combination["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })


    def test_setup_session_requires_both_setup_and_session(self):
        trades = [
            {
                "id": "setup-only-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "setup-only-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "result": "LOSS",
            },
            {
                "id": "session-only-1",
                "timestamp": "2026-08-03T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "session-only-2",
                "timestamp": "2026-08-04T10:00:00Z",
                "session": "LONDON",
                "result": "LOSS",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        self.assertFalse(
            any(finding["dimension"] == "setup_session" for finding in findings)
        )

    def test_finding_discovers_setup_regime_combination(self):
        trades = [
            {
                "id": "setup-regime-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "setup-regime-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "result": "LOSS",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "setup-regime-3",
                "timestamp": "2026-08-03T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "other-regime",
                "timestamp": "2026-08-04T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "RANGING"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        combination = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup_regime"
            and finding["value"] == "breakout + TRENDING"
        )

        self.assertEqual(combination["sampleSize"], 3)
        self.assertEqual(
            combination["sourceTradeIds"],
            [
                "setup-regime-1",
                "setup-regime-2",
                "setup-regime-3",
            ],
        )
        self.assertEqual(combination["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })


    def test_setup_regime_requires_both_setup_and_regime(self):
        trades = [
            {
                "id": "setup-only-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "setup-only-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "result": "LOSS",
            },
            {
                "id": "regime-only-1",
                "timestamp": "2026-08-03T10:00:00Z",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "regime-only-2",
                "timestamp": "2026-08-04T10:00:00Z",
                "result": "LOSS",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        self.assertFalse(
            any(
                finding["dimension"] == "setup_regime"
                for finding in findings
            )
        )


    def test_finding_discovers_setup_session_regime_combination(self):
        trades = [
            {
                "id": "setup-session-regime-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "setup-session-regime-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "LOSS",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "setup-session-regime-3",
                "timestamp": "2026-08-03T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "other-combination",
                "timestamp": "2026-08-04T10:00:00Z",
                "setup": "breakout",
                "session": "NEW_YORK",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "RANGING"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        combination = next(
            finding
            for finding in findings
            if finding["dimension"] == "setup_session_regime"
            and finding["value"] == "breakout + LONDON + TRENDING"
        )

        self.assertEqual(combination["sampleSize"], 3)
        self.assertEqual(
            combination["sourceTradeIds"],
            [
                "setup-session-regime-1",
                "setup-session-regime-2",
                "setup-session-regime-3",
            ],
        )
        self.assertEqual(combination["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })


    def test_setup_session_regime_requires_all_three_fields(self):
        trades = [
            {
                "id": "setup-only-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
            },
            {
                "id": "setup-session-1",
                "timestamp": "2026-08-02T10:00:00Z",
                "setup": "breakout",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "setup-regime-1",
                "timestamp": "2026-08-03T10:00:00Z",
                "setup": "breakout",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
            {
                "id": "session-regime-1",
                "timestamp": "2026-08-04T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=1)

        self.assertFalse(
            any(
                finding["dimension"] == "setup_session_regime"
                for finding in findings
            )
        )


    def test_finding_discovers_structure_session_combination(self):
        trades = [
            {
                "id": "structure-session-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketStructure": {"state": "BULLISH"},
                },
            },
            {
                "id": "structure-session-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "session": "LONDON",
                "result": "LOSS",
                "intelligence": {
                    "marketStructure": {"state": "BULLISH"},
                },
            },
            {
                "id": "structure-session-3",
                "timestamp": "2026-08-03T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
                "intelligence": {
                    "marketStructure": {"state": "BULLISH"},
                },
            },
            {
                "id": "other-structure-session",
                "timestamp": "2026-08-04T10:00:00Z",
                "session": "NEW_YORK",
                "result": "WIN",
                "intelligence": {
                    "marketStructure": {"state": "BEARISH"},
                },
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        combination = next(
            finding
            for finding in findings
            if finding["dimension"] == "structure_session"
            and finding["value"] == "BULLISH + LONDON"
        )

        self.assertEqual(combination["sampleSize"], 3)
        self.assertEqual(
            combination["sourceTradeIds"],
            [
                "structure-session-1",
                "structure-session-2",
                "structure-session-3",
            ],
        )
        self.assertEqual(combination["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })


    def test_structure_session_requires_both_structure_and_session(self):
        trades = [
            {
                "id": "structure-only-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "result": "WIN",
                "intelligence": {
                    "marketStructure": {"state": "BULLISH"},
                },
            },
            {
                "id": "structure-only-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "result": "LOSS",
                "intelligence": {
                    "marketStructure": {"state": "BULLISH"},
                },
            },
            {
                "id": "session-only-1",
                "timestamp": "2026-08-03T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "session-only-2",
                "timestamp": "2026-08-04T10:00:00Z",
                "session": "LONDON",
                "result": "LOSS",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        self.assertFalse(
            any(
                finding["dimension"] == "structure_session"
                for finding in findings
            )
        )


    def test_finding_discovers_direction_session_combination(self):
        trades = [
            {
                "id": "direction-session-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "direction": "LONG",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "direction-session-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "direction": "LONG",
                "session": "LONDON",
                "result": "LOSS",
            },
            {
                "id": "direction-session-3",
                "timestamp": "2026-08-03T10:00:00Z",
                "direction": "LONG",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "other-direction-session",
                "timestamp": "2026-08-04T10:00:00Z",
                "direction": "SHORT",
                "session": "NEW_YORK",
                "result": "WIN",
            },
        ]

        findings = discover_patterns(trades, min_sample=3)

        combination = next(
            finding
            for finding in findings
            if finding["dimension"] == "direction_session"
            and finding["value"] == "LONG + LONDON"
        )

        self.assertEqual(combination["sampleSize"], 3)
        self.assertEqual(
            combination["sourceTradeIds"],
            [
                "direction-session-1",
                "direction-session-2",
                "direction-session-3",
            ],
        )
        self.assertEqual(combination["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 0,
        })


    def test_direction_session_requires_both_direction_and_session(self):
        trades = [
            {
                "id": "direction-only-1",
                "timestamp": "2026-08-01T10:00:00Z",
                "direction": "LONG",
                "result": "WIN",
            },
            {
                "id": "direction-only-2",
                "timestamp": "2026-08-02T10:00:00Z",
                "direction": "LONG",
                "result": "LOSS",
            },
            {
                "id": "session-only-1",
                "timestamp": "2026-08-03T10:00:00Z",
                "session": "LONDON",
                "result": "WIN",
            },
            {
                "id": "session-only-2",
                "timestamp": "2026-08-04T10:00:00Z",
                "session": "LONDON",
                "result": "LOSS",
            },
        ]

        findings = discover_patterns(trades, min_sample=2)

        self.assertFalse(
            any(
                finding["dimension"] == "direction_session"
                for finding in findings
            )
        )


    def test_does_not_create_findings_below_minimum_sample(self):
        trades = [
            {
                "id": "trade-1",
                "timestamp": "2026-08-01T10:00:00.000Z",
                "setup": "rare",
                "result": "WIN",
            },
            {
                "id": "trade-2",
                "timestamp": "2026-08-02T10:00:00.000Z",
                "setup": "rare",
                "result": "WIN",
            },
        ]

        self.assertEqual(discover_patterns(trades, min_sample=3), [])


if __name__ == "__main__":
    unittest.main()

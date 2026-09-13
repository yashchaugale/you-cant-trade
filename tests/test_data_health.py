import unittest

from services.data_health import assess_data_health


class DataHealthTests(unittest.TestCase):
    def test_reports_completeness_and_analysis_readiness(self):
        trades = [
            {
                "id": "ready",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "exitPrice": 110,
                "result": "WIN",
                "intelligence": {
                    "marketContext": {"regime": "TRENDING"},
                    "marketStructure": {"state": "BULLISH"},
                    "setupFingerprint": {
                        "features": ["LONG"],
                        "tags": ["STRUCTURE_ALIGNED"],
                    },
                    "calculated": {
                        "features": {"actualR": 2.0},
                    },
                },
            },
            {
                "id": "incomplete",
                "entry": None,
                "stopLoss": None,
                "takeProfit": 100,
                "exitPrice": None,
                "result": "LOSS",
                "intelligence": {},
            },
            {
                "id": "unreviewed",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "exitPrice": None,
                "result": None,
                "intelligence": {},
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(health["computationVersion"], 1)
        self.assertEqual(health["totalTrades"], 3)
        self.assertEqual(health["reviewedTrades"], 2)
        self.assertEqual(health["unreviewedTrades"], 1)

        self.assertEqual(health["missing"]["outcome"], 1)
        self.assertEqual(health["missing"]["entry"], 1)
        self.assertEqual(health["missing"]["stopLoss"], 1)
        self.assertEqual(health["missing"]["takeProfit"], 0)
        self.assertEqual(health["missing"]["exitPriceReviewed"], 1)
        self.assertEqual(health["missing"]["actualRReviewed"], 1)
        self.assertEqual(health["missing"]["marketContext"], 2)
        self.assertEqual(health["missing"]["marketStructure"], 2)
        self.assertEqual(health["missing"]["setupFingerprint"], 2)

        self.assertEqual(health["analysisReadyTrades"], 1)

    def test_reports_invalid_risk_dates_duplicates_and_date_coverage(self):
        trades = [
            {
                "id": "valid",
                "timestamp": "2026-01-10T10:00:00Z",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
            },
            {
                "id": "bad-risk",
                "timestamp": "2026-02-15T10:00:00Z",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 100,
                "takeProfit": 110,
                "result": "LOSS",
            },
            {
                "id": "bad-date",
                "timestamp": "not-a-date",
                "direction": "SHORT",
                "entry": 100,
                "stopLoss": 105,
                "takeProfit": 90,
                "result": "WIN",
            },
            {
                "id": "valid",
                "timestamp": "2026-03-20T10:00:00Z",
                "direction": "SHORT",
                "entry": 100,
                "stopLoss": 105,
                "takeProfit": 90,
                "result": "LOSS",
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(health["invalid"]["risk"], 1)
        self.assertEqual(health["invalid"]["timestamp"], 1)
        self.assertEqual(health["invalid"]["record"], 1)
        self.assertEqual(health["duplicates"]["ids"], 1)

        self.assertEqual(
            health["dateCoverage"]["earliest"],
            "2026-01-10T10:00:00+00:00",
        )
        self.assertEqual(
            health["dateCoverage"]["latest"],
            "2026-03-20T10:00:00+00:00",
        )
        self.assertEqual(
            health["dateCoverage"]["validTimestampCount"],
            3,
        )

    def test_reports_missing_core_trade_and_review_fields(self):
        trades = [
            {
                "id": "complete",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "exitPrice": 110,
                "result": "WIN",
                "setup": "breakout",
                "session": "NEW_YORK",
            },
            {
                "id": "missing",
                "symbol": "",
                "timeframe": None,
                "direction": None,
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "exitPrice": None,
                "result": None,
                "setup": "",
                "session": None,
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(health["missing"]["symbol"], 1)
        self.assertEqual(health["missing"]["timeframe"], 1)
        self.assertEqual(health["missing"]["direction"], 1)
        self.assertEqual(health["missing"]["setup"], 1)
        self.assertEqual(health["missing"]["session"], 1)

    def test_missing_fields_are_independent_of_other_trade_fields(self):
        trades = [
            {
                "id": "trade-1",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": None,
                "stopLoss": None,
                "takeProfit": None,
                "result": None,
                "setup": None,
                "session": None,
            },
            {
                "id": "trade-2",
                "symbol": None,
                "timeframe": None,
                "direction": None,
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
                "setup": "breakout",
                "session": "LONDON",
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(health["missing"]["symbol"], 1)
        self.assertEqual(health["missing"]["timeframe"], 1)
        self.assertEqual(health["missing"]["direction"], 1)
        self.assertEqual(health["missing"]["entry"], 1)
        self.assertEqual(health["missing"]["stopLoss"], 1)
        self.assertEqual(health["missing"]["takeProfit"], 1)
        self.assertEqual(health["missing"]["outcome"], 1)
        self.assertEqual(health["missing"]["setup"], 1)
        self.assertEqual(health["missing"]["session"], 1)

    def test_reports_incomplete_trades_once_per_trade(self):
        trades = [
            {
                "id": "complete",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
            },
            {
                "id": "missing-many",
                "symbol": None,
                "timeframe": None,
                "direction": None,
                "entry": None,
                "stopLoss": None,
                "takeProfit": None,
                "result": None,
            },
            {
                "id": "missing-one",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": None,
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(
            health["incompleteTrades"],
            {
                "count": 2,
                "total": 3,
            },
        )

    def test_incomplete_trade_requires_core_capture_fields_only(self):
        trades = [
            {
                "id": "unreviewed",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
                "exitPrice": None,
            },
            {
                "id": "complete-core",
                "symbol": "NQ",
                "timeframe": "5m",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
            },
        ]

        health = assess_data_health(trades)

        self.assertEqual(
            health["incompleteTrades"],
            {
                "count": 0,
                "total": 2,
            },
        )

    def test_incomplete_trades_empty_journal(self):
        health = assess_data_health([])

        self.assertEqual(
            health["incompleteTrades"],
            {
                "count": 0,
                "total": 0,
            },
        )

    def test_data_health_does_not_mutate_trades(self):
        trades = [
            {
                "id": "trade-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "takeProfit": 110,
                "result": "WIN",
            }
        ]

        original = [trade.copy() for trade in trades]

        assess_data_health(trades)

        self.assertEqual(trades, original)


if __name__ == "__main__":
    unittest.main()

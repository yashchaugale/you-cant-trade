import os
import tempfile
import unittest
import importlib


class LocalDatabaseCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["YOU_CANT_TRADE_DATA_DIR"] = self.temp_dir.name
        import database.local_database as database
        database = importlib.reload(database)
        self.database = database
        database.initialise()

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("YOU_CANT_TRADE_DATA_DIR", None)

    def test_canonical_intelligence_round_trip(self):
        trade = {
            "id": "fixture-db-trade",
            "schemaVersion": 4,
            "timestamp": "2026-08-27T10:00:00.000Z",
            "updatedAt": "2026-08-27T10:00:00.000Z",
            "symbol": "BTCUSD",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 95,
            "takeProfit": 110,
            "intelligence": {"marketContext": {"trend": None}},
        }
        saved = self.database.upsert_trade(trade)
        self.assertEqual(saved["schemaVersion"], 4)
        self.assertEqual(saved["intelligence"]["marketContext"]["trend"], None)

    def test_legacy_rows_are_read_after_migration(self):
        with self.database.connect() as connection:
            connection.execute("insert into trades (id, schema_version, captured_at, updated_at) values (?, ?, ?, ?)", ("legacy", 3, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
        self.database.initialise()
        legacy = self.database.get_trade("legacy")
        self.assertIsNotNone(legacy)
        self.assertEqual(legacy["schemaVersion"], 4)
        self.assertIn("marketStructure", legacy["intelligence"])

    def test_similarity_prefers_canonical_market_context_and_structure(self):
        source = {
            "id": "source",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "setup": "breakout",
            "intelligence": {
                "marketContext": {
                    "regime": "CONTRACTING",
                    "direction": "DOWN",
                },
                "marketStructure": {
                    "state": "BEARISH",
                    "events": [
                        {"event": "BEARISH_BOS", "time": 100},
                    ],
                },
                "setupFingerprint": {
                    "features": [
                        "LONG",
                        "CONTRACTING",
                        "BEARISH_STRUCTURE",
                    ],
                    "tags": ["COUNTER_STRUCTURE"],
                },
            },
        }

        canonical_match = {
            "id": "canonical-match",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "setup": "different-setup",
            "intelligence": {
                "marketContext": {
                    "regime": "CONTRACTING",
                    "direction": "DOWN",
                },
                "marketStructure": {
                    "state": "BEARISH",
                    "events": [
                        {"event": "BEARISH_BOS", "time": 200},
                    ],
                },
                "setupFingerprint": {
                    "features": [
                        "LONG",
                        "CONTRACTING",
                        "BEARISH_STRUCTURE",
                    ],
                    "tags": ["COUNTER_STRUCTURE"],
                },
            },
        }

        journal_match = {
            "id": "journal-match",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "setup": "breakout",
            "intelligence": {
                "marketContext": {
                    "regime": "EXPANDING",
                    "direction": "UP",
                },
                "marketStructure": {
                    "state": "BULLISH",
                    "events": [
                        {"event": "BULLISH_BOS", "time": 200},
                    ],
                },
                "setupFingerprint": {
                    "features": ["LONG"],
                    "tags": [],
                },
            },
        }

        canonical_score = self.database._canonical_similarity_score(
            source,
            canonical_match,
        )
        journal_score = self.database._canonical_similarity_score(
            source,
            journal_match,
        )

        self.assertGreater(canonical_score, journal_score)

    def test_similarity_does_not_use_result(self):
        source = {
            "id": "source",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "result": "WIN",
            "intelligence": {
                "marketContext": {
                    "regime": "CONTRACTING",
                    "direction": "DOWN",
                },
                "marketStructure": {
                    "state": "BEARISH",
                },
                "setupFingerprint": {
                    "features": ["LONG", "CONTRACTING"],
                    "tags": ["COUNTER_STRUCTURE"],
                },
            },
        }

        same_context_win = {
            "id": "win",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "result": "WIN",
            "intelligence": source["intelligence"],
        }

        same_context_loss = {
            "id": "loss",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "result": "LOSS",
            "intelligence": source["intelligence"],
        }

        win_score = self.database._canonical_similarity_score(
            source,
            same_context_win,
        )
        loss_score = self.database._canonical_similarity_score(
            source,
            same_context_loss,
        )

        self.assertEqual(win_score, loss_score)

    def test_similarity_supports_trades_without_intelligence(self):
        source = {
            "id": "source",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "setup": "breakout",
            "session": "LONDON",
            "intelligence": {},
        }

        legacy_match = {
            "id": "legacy",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "setup": "breakout",
            "session": "LONDON",
            "intelligence": {},
        }

        score = self.database._canonical_similarity_score(
            source,
            legacy_match,
        )

        self.assertEqual(score, 14)

    def test_build_historical_context_returns_compact_comparable_evidence(self):
        source = {
            "id": "source",
            "schemaVersion": 4,
            "timestamp": "2026-08-27T10:00:00.000Z",
            "updatedAt": "2026-08-27T10:00:00.000Z",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 95,
            "takeProfit": 110,
            "result": "WIN",
            "exitPrice": 110,
            "setup": "breakout",
            "session": "LONDON",
            "intelligence": {
                "marketContext": {
                    "regime": "CONTRACTING",
                    "direction": "DOWN",
                },
                "marketStructure": {
                    "state": "BEARISH",
                    "events": [
                        {"event": "BEARISH_BOS", "time": 100},
                    ],
                },
                "setupFingerprint": {
                    "features": [
                        "LONG",
                        "CONTRACTING",
                        "BEARISH_STRUCTURE",
                    ],
                    "tags": ["COUNTER_STRUCTURE"],
                },
                "calculated": {
                    "features": {
                        "plannedRR": 2.0,
                    }
                },
            },
        }

        similar = {
            **source,
            "id": "similar",
            "timestamp": "2026-08-26T10:00:00.000Z",
            "result": "WIN",
            "exitPrice": 110,
        }

        self.database.upsert_trade(source)
        self.database.upsert_trade(similar)

        context = self.database.build_historical_context(
            "source",
            limit=10,
        )

        self.assertEqual(
            context["similarTradeIds"],
            ["similar"],
        )
        self.assertEqual(
            context["sampleSize"],
            1,
        )
        self.assertEqual(
            context["similarityScore"],
            self.database._canonical_similarity_score(source, similar),
        )

        stats = context["comparableStats"]

        self.assertEqual(stats["reviewedSampleSize"], 1)
        self.assertEqual(stats["wins"], 1)
        self.assertEqual(stats["losses"], 0)
        self.assertEqual(stats["breakEven"], 0)
        self.assertEqual(stats["winRate"], 1.0)
        self.assertEqual(stats["actualR"]["count"], 1)
        self.assertEqual(stats["actualR"]["average"], 2.0)
        self.assertEqual(stats["plannedRR"]["count"], 1)
        self.assertEqual(stats["plannedRR"]["average"], 2.0)

        self.assertIn("CONTRACTING", context["patternReferences"])
        self.assertIn("BEARISH_STRUCTURE", context["patternReferences"])
        self.assertIn("COUNTER_STRUCTURE", context["patternReferences"])

        self.assertNotIn("marketStructure", stats)
        self.assertNotIn("marketStructure", context)


    def test_historical_context_includes_compact_ranked_matches(self):
        source = {
            "id": "source",
            "schemaVersion": 4,
            "timestamp": "2026-08-27T10:00:00.000Z",
            "updatedAt": "2026-08-27T10:00:00.000Z",
            "symbol": "BTCUSD",
            "timeframe": "15m",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 95,
            "takeProfit": 110,
            "result": "WIN",
            "intelligence": {
                "marketContext": {
                    "regime": "CONTRACTING",
                    "direction": "DOWN",
                },
                "marketStructure": {
                    "state": "BEARISH",
                },
                "setupFingerprint": {
                    "features": [
                        "LONG",
                        "CONTRACTING",
                        "BEARISH_STRUCTURE",
                    ],
                    "tags": ["COUNTER_STRUCTURE"],
                },
                "calculated": {
                    "features": {
                        "plannedRR": 2.0,
                    }
                },
            },
        }

        similar = {
            **source,
            "id": "similar",
            "timestamp": "2026-08-26T10:00:00.000Z",
            "result": "LOSS",
        }

        self.database.upsert_trade(source)
        self.database.upsert_trade(similar)

        context = self.database.build_historical_context(
            "source",
            limit=10,
        )

        matches = context["matches"]

        self.assertEqual(len(matches), 1)

        match = matches[0]

        self.assertEqual(match["id"], "similar")
        self.assertEqual(
            match["similarityScore"],
            self.database._canonical_similarity_score(source, similar),
        )
        self.assertEqual(match["symbol"], "BTCUSD")
        self.assertEqual(match["timeframe"], "15m")
        self.assertEqual(match["direction"], "LONG")
        self.assertEqual(match["result"], "LOSS")
        self.assertEqual(match["marketRegime"], "CONTRACTING")
        self.assertEqual(match["structureState"], "BEARISH")
        self.assertEqual(
            match["setupFeatures"],
            ["LONG", "CONTRACTING", "BEARISH_STRUCTURE"],
        )
        self.assertEqual(
            match["setupTags"],
            ["COUNTER_STRUCTURE"],
        )
        self.assertEqual(match["plannedRR"], 2.0)

        self.assertNotIn("marketStructure", match)
        self.assertNotIn("notes", match)
        self.assertNotIn("emotions", match)


if __name__ == "__main__":
    unittest.main()




    def test_memory_finding_persistence_and_verification(self):
        trade = {
            "id": "MEMORY_TEST_TRADE",
            "schemaVersion": 4,
            "timestamp": "2026-08-27T10:00:00.000Z",
            "updatedAt": "2026-08-27T10:00:00.000Z",
            "symbol": "TEST",
            "direction": "LONG",
            "entry": 100,
            "stopLoss": 99,
            "takeProfit": 102,
            "intelligence": {"marketContext": {"trend": None}},
        }

        self.database.upsert_trade(trade)

        finding = self.database.create_memory_finding({
            "id": "MEMORY_TEST_FINDING",
            "type": "EDGE",
            "statement": "Test memory finding.",
            "sampleSize": 3,
            "evidenceStrength": "LIMITED",
            "firstObserved": "2026-01-01T10:00:00Z",
            "lastVerified": None,
            "status": "OBSERVED",
            "contractVersion": 1,
            "supportingTradeIds": ["MEMORY_TEST_TRADE"],
        })

        self.assertEqual(finding["id"], "MEMORY_TEST_FINDING")
        self.assertEqual(
            finding["supportingTradeIds"],
            ["MEMORY_TEST_TRADE"],
        )

        verification = self.database.save_memory_verification(
            "MEMORY_TEST_FINDING",
            {
                "id": "MEMORY_TEST_VERIFICATION",
                "verifiedAt": "2026-02-01T10:00:00Z",
                "status": "ACTIVE",
                "sampleSize": 5,
                "evidenceStrength": "MODERATE",
                "supportingTradeIds": ["MEMORY_TEST_TRADE"],
                "contractVersion": 1,
            },
        )

        self.assertEqual(
            verification["findingId"],
            "MEMORY_TEST_FINDING",
        )
        self.assertEqual(verification["status"], "ACTIVE")

        updated = self.database.get_memory_finding("MEMORY_TEST_FINDING")
        self.assertEqual(
            updated["lastVerified"],
            "2026-02-01T10:00:00Z",
        )
        self.assertEqual(updated["status"], "ACTIVE")
        self.assertEqual(updated["sampleSize"], 5)
        self.assertEqual(updated["evidenceStrength"], "MODERATE")

        history = self.database.list_memory_verifications(
            "MEMORY_TEST_FINDING"
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(
            history[0]["id"],
            "MEMORY_TEST_VERIFICATION",
        )

        self.database.delete_trade("MEMORY_TEST_TRADE")
        self.assertIsNone(
            self.database.get_memory_finding("MEMORY_TEST_FINDING")
        )


    def test_memory_finding_rejects_unknown_supporting_trade(self):
        with self.assertRaises(Exception) as context:
            self.database.create_memory_finding({
                "id": "MEMORY_BAD_FINDING",
                "type": "EDGE",
                "statement": "Should fail.",
                "sampleSize": 3,
                "evidenceStrength": "LIMITED",
                "firstObserved": "2026-01-01T10:00:00Z",
                "status": "OBSERVED",
                "contractVersion": 1,
                "supportingTradeIds": ["DOES_NOT_EXIST"],
            })

        self.assertTrue(
            "FOREIGN KEY" in str(context.exception).upper()
            or "constraint" in str(context.exception).lower()
        )

import unittest

from services.deterministic_analytics import calculate_journal_analytics


class DeterministicAnalyticsTests(unittest.TestCase):

    def test_win_rate_excludes_break_even_and_unknown_outcomes(self):
        trades = [
            {"result": "WIN"},
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "BE"},
            {"result": None},
            {"result": None},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winRate"], 0.666667)
        self.assertEqual(stats["reviewedTrades"], 4)
        self.assertEqual(stats["outcomes"], {
            "wins": 2,
            "losses": 1,
            "breakEven": 1,
        })

    def test_win_rate_is_none_when_no_decided_trades_exist(self):
        trades = [
            {"result": "BE"},
            {"result": None},
            {"result": None},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["winRate"])

    def test_win_rate_does_not_require_review_fields(self):
        trades = [
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "WIN"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winRate"], 0.666667)
        self.assertEqual(stats["reviewedTrades"], 3)


    def test_win_streak_returns_maximum_consecutive_wins(self):
        trades = [
            {"result": "LOSS", "timestamp": "2026-01-01T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-02T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-03T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-04T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-05T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winStreak"]["value"], 2)
        self.assertEqual(stats["winStreak"]["count"], 5)

    def test_win_streak_uses_chronological_order(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-03T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-04T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-01T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-02T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winStreak"]["value"], 3)

    def test_win_streak_breaks_on_break_even_and_unknown_outcomes(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T09:00:00"},
            {"result": "BE", "timestamp": "2026-01-02T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-03T09:00:00"},
            {"result": None, "timestamp": "2026-01-04T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-05T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-06T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winStreak"]["value"], 2)
        self.assertEqual(stats["winStreak"]["count"], 6)

    def test_win_streak_is_zero_without_wins(self):
        trades = [
            {"result": "LOSS", "timestamp": "2026-01-01T09:00:00"},
            {"result": "BE", "timestamp": "2026-01-02T09:00:00"},
            {"result": None, "timestamp": "2026-01-03T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["winStreak"]["value"], 0)
        self.assertEqual(stats["winStreak"]["count"], 3)


    def test_loss_streak_returns_maximum_consecutive_losses(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-02T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-03T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-04T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-05T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["lossStreak"]["value"], 2)
        self.assertEqual(stats["lossStreak"]["count"], 5)

    def test_loss_streak_uses_chronological_order(self):
        trades = [
            {"result": "LOSS", "timestamp": "2026-01-03T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-04T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-01T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-02T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["lossStreak"]["value"], 3)

    def test_loss_streak_breaks_on_win_break_even_and_unknown_outcomes(self):
        trades = [
            {"result": "LOSS", "timestamp": "2026-01-01T09:00:00"},
            {"result": "WIN", "timestamp": "2026-01-02T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-03T09:00:00"},
            {"result": "BE", "timestamp": "2026-01-04T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-05T09:00:00"},
            {"result": None, "timestamp": "2026-01-06T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-07T09:00:00"},
            {"result": "LOSS", "timestamp": "2026-01-08T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["lossStreak"]["value"], 2)
        self.assertEqual(stats["lossStreak"]["count"], 8)

    def test_loss_streak_is_zero_without_losses(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T09:00:00"},
            {"result": "BE", "timestamp": "2026-01-02T09:00:00"},
            {"result": None, "timestamp": "2026-01-03T09:00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["lossStreak"]["value"], 0)
        self.assertEqual(stats["lossStreak"]["count"], 3)


    def test_hour_groups_trades_by_utc_hour(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T09:15:00Z"},
            {"result": "LOSS", "timestamp": "2026-01-02T09:45:00Z"},
            {"result": "WIN", "timestamp": "2026-01-03T14:10:00Z"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byHour"], [
            {"hour": 9, "count": 2},
            {"hour": 14, "count": 1},
        ])

    def test_hour_normalizes_offset_timestamps_to_utc(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T10:00:00+01:00"},
            {"result": "LOSS", "timestamp": "2026-01-01T05:00:00-04:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byHour"], [
            {"hour": 9, "count": 2},
        ])

    def test_hour_excludes_invalid_and_missing_timestamps(self):
        trades = [
            {"result": "WIN", "timestamp": "2026-01-01T09:00:00Z"},
            {"result": "LOSS", "timestamp": "not-a-date"},
            {"result": "WIN"},
            {"result": "LOSS", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byHour"], [
            {"hour": 9, "count": 1},
        ])

    def test_hour_returns_empty_when_no_valid_timestamps_exist(self):
        trades = [
            {"result": "WIN", "timestamp": "not-a-date"},
            {"result": "LOSS"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byHour"], [])

    def test_average_r_uses_realized_actual_r_only(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["count"], 3)
        self.assertEqual(stats["actualR"]["total"], 1.0)
        self.assertEqual(stats["actualR"]["average"], 0.333333)

    def test_average_r_excludes_trades_without_calculable_actual_r(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": None,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["count"], 1)
        self.assertEqual(stats["actualR"]["average"], 2.0)

    def test_average_r_is_none_when_no_actual_r_can_be_calculated(self):
        trades = [
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "BE"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["count"], 0)
        self.assertIsNone(stats["actualR"]["average"])

    def test_median_r_uses_middle_realized_actual_r_value(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["median"], 1.0)

    def test_median_r_averages_two_middle_values_for_even_sample(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 115,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["median"], 1.5)

    def test_median_r_is_none_when_no_actual_r_can_be_calculated(self):
        stats = calculate_journal_analytics([
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "BE"},
        ])

        self.assertIsNone(stats["actualR"]["median"])

    def test_average_winner_uses_only_positive_actual_r(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["averageWinner"]["value"], 1.5)
        self.assertEqual(stats["averageWinner"]["count"], 2)

    def test_average_winner_excludes_trades_without_actual_r_evidence(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 120,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 130,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["averageWinner"]["value"], 3.0)
        self.assertEqual(stats["averageWinner"]["count"], 2)

    def test_average_winner_is_none_when_no_positive_actual_r_exists(self):
        trades = [
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["averageWinner"]["value"])
        self.assertEqual(stats["averageWinner"]["count"], 0)

    def test_average_loser_uses_only_negative_actual_r(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 97.5,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["averageLoser"]["value"], -0.75)
        self.assertEqual(stats["averageLoser"]["count"], 2)

    def test_average_loser_excludes_trades_without_actual_r_evidence(self):
        trades = [
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 97.5,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["averageLoser"]["value"], -0.75)
        self.assertEqual(stats["averageLoser"]["count"], 2)

    def test_average_loser_is_none_when_no_negative_actual_r_exists(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["averageLoser"]["value"])
        self.assertEqual(stats["averageLoser"]["count"], 0)

    def test_biggest_winner_returns_largest_positive_actual_r(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 120,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["biggestWinner"]["value"], 4.0)
        self.assertEqual(stats["biggestWinner"]["count"], 2)

    def test_biggest_winner_excludes_trades_without_actual_r_evidence(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 115,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 130,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["biggestWinner"]["value"], 3.0)
        self.assertEqual(stats["biggestWinner"]["count"], 2)

    def test_biggest_winner_is_none_when_no_positive_actual_r_exists(self):
        trades = [
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["biggestWinner"]["value"])
        self.assertEqual(stats["biggestWinner"]["count"], 0)

    def test_biggest_loser_returns_most_negative_actual_r(self):
        trades = [
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 90,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["biggestLoser"]["value"], -2.0)
        self.assertEqual(stats["biggestLoser"]["count"], 2)

    def test_biggest_loser_excludes_trades_without_actual_r_evidence(self):
        trades = [
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 90,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 80,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["biggestLoser"]["value"], -2.0)
        self.assertEqual(stats["biggestLoser"]["count"], 2)

    def test_biggest_loser_is_none_when_no_negative_actual_r_exists(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["biggestLoser"]["value"])
        self.assertEqual(stats["biggestLoser"]["count"], 0)

    def test_drawdown_uses_chronological_actual_r_sequence(self):
        trades = [
            {
                "timestamp": "2026-01-03T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 97.5,
            },
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "timestamp": "2026-01-02T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 97.5,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["drawdown"]["value"], 1.0)
        self.assertEqual(stats["drawdown"]["count"], 3)

    def test_drawdown_returns_peak_to_trough_decline(self):
        trades = [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "timestamp": "2026-01-02T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "timestamp": "2026-01-03T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["drawdown"]["value"], 2.0)
        self.assertEqual(stats["drawdown"]["count"], 3)

    def test_drawdown_excludes_trades_without_actual_r_evidence(self):
        trades = [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "timestamp": "2026-01-02T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "timestamp": "2026-01-03T10:00:00Z",
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["drawdown"]["value"], 1.0)
        self.assertEqual(stats["drawdown"]["count"], 2)

    def test_drawdown_is_zero_when_equity_never_declines_from_peak(self):
        trades = [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "timestamp": "2026-01-02T10:00:00Z",
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["drawdown"]["value"], 0.0)
        self.assertEqual(stats["drawdown"]["count"], 2)

    def test_drawdown_is_zero_without_actual_r_evidence(self):
        stats = calculate_journal_analytics([
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "BE"},
        ])

        self.assertEqual(stats["drawdown"]["value"], 0.0)
        self.assertEqual(stats["drawdown"]["count"], 0)

    def test_expectancy_uses_same_actual_r_population(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["actualR"]["count"], 3)
        self.assertEqual(stats["actualR"]["average"], 0.333333)
        self.assertEqual(stats["expectancy"]["value"], 0.333333)
        self.assertEqual(stats["expectancy"]["count"], 3)
        self.assertEqual(stats["expectancy"]["outcomes"], {
            "wins": 1,
            "losses": 1,
            "breakEven": 1,
        })

    def test_expectancy_is_none_without_actual_r_evidence(self):
        trades = [
            {"result": "WIN"},
            {"result": "LOSS"},
            {"result": "BE"},
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["expectancy"]["value"])
        self.assertEqual(stats["expectancy"]["count"], 0)
        self.assertEqual(stats["expectancy"]["outcomes"], {
            "wins": 0,
            "losses": 0,
            "breakEven": 0,
        })

    def test_expectancy_excludes_invalid_direction_from_evidence(self):
        trades = [
            {
                "result": "WIN",
                "direction": "SIDEWAYS",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["expectancy"]["count"], 1)
        self.assertEqual(stats["expectancy"]["value"], -1.0)
        self.assertEqual(stats["expectancy"]["outcomes"], {
            "wins": 0,
            "losses": 1,
            "breakEven": 0,
        })

    def test_profit_factor_uses_gross_profit_over_gross_loss(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 97.5,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["profitFactor"]["value"], 2.0)
        self.assertEqual(stats["profitFactor"]["count"], 5)
        self.assertEqual(stats["profitFactor"]["grossProfit"], 3.0)
        self.assertEqual(stats["profitFactor"]["grossLoss"], 1.5)

    def test_profit_factor_is_none_when_there_is_no_gross_loss(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "BE",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 100,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertIsNone(stats["profitFactor"]["value"])
        self.assertEqual(stats["profitFactor"]["count"], 2)
        self.assertEqual(stats["profitFactor"]["grossProfit"], 2.0)
        self.assertEqual(stats["profitFactor"]["grossLoss"], 0.0)

    def test_profit_factor_excludes_missing_actual_r_evidence(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
            {
                "result": "LOSS",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": None,
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 95,
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["profitFactor"]["value"], 2.0)
        self.assertEqual(stats["profitFactor"]["count"], 2)
        self.assertEqual(stats["profitFactor"]["grossProfit"], 2.0)
        self.assertEqual(stats["profitFactor"]["grossLoss"], 1.0)

    def test_calculates_reviewed_outcomes_actual_r_and_top_fields(self):
        trades = [
            {
                "result": "WIN",
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 110,
                "setup": "Breakout",
                "emotions": ["calm", "focused"],
                "executionTag": "planned",
            },
            {
                "result": "LOSS",
                "direction": "SHORT",
                "entry": 100,
                "stopLoss": 105,
                "exitPrice": 110,
                "setup": "Breakout",
                "emotions": ["frustrated"],
                "executionTag": "late",
            },
            {
                "result": None,
                "direction": "LONG",
                "entry": 100,
                "stopLoss": 95,
                "exitPrice": 105,
                "setup": "Ignored",
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["totalTrades"], 3)
        self.assertEqual(stats["reviewedTrades"], 2)
        self.assertEqual(stats["winRate"], 0.5)
        self.assertEqual(stats["outcomes"], {
            "wins": 1,
            "losses": 1,
            "breakEven": 0,
        })
        self.assertEqual(stats["actualR"]["count"], 2)
        self.assertEqual(stats["actualR"]["total"], 0.0)
        self.assertEqual(stats["actualR"]["average"], 0.0)
        self.assertEqual(stats["topSetups"], [{"value": "Breakout", "count": 2}])
        self.assertEqual(stats["topEmotions"][0], {"value": "calm", "count": 1})
        self.assertEqual(stats["topExecutionTags"], [
            {"value": "late", "count": 1},
            {"value": "planned", "count": 1},
        ])
        self.assertIn("at least 10 trades", stats["sampleWarning"])


    def test_session_groups_trades_by_canonical_session(self):
        trades = [
            {"id": "1", "session": "LONDON"},
            {"id": "2", "session": "ASIA"},
            {"id": "3", "session": "LONDON"},
            {"id": "4", "session": "NEW_YORK"},
            {"id": "5", "session": "OTHER"},
            {"id": "6", "session": "ASIA"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["bySession"], [
            {"session": "ASIA", "count": 2},
            {"session": "LONDON", "count": 2},
            {"session": "NEW_YORK", "count": 1},
            {"session": "OTHER", "count": 1},
        ])

    def test_session_excludes_missing_and_invalid_sessions(self):
        trades = [
            {"id": "1", "session": "LONDON"},
            {"id": "2", "session": None},
            {"id": "3"},
            {"id": "4", "session": ""},
            {"id": "5", "session": "INVALID"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["bySession"], [
            {"session": "LONDON", "count": 1},
        ])

    def test_session_returns_empty_when_no_valid_sessions_exist(self):
        trades = [
            {"id": "1", "session": None},
            {"id": "2"},
            {"id": "3", "session": "INVALID"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["bySession"], [])

    def test_session_does_not_infer_session_from_timestamp(self):
        trades = [
            {
                "id": "1",
                "session": None,
                "timestamp": "2026-01-05T09:00:00Z",
            },
            {
                "id": "2",
                "timestamp": "2026-01-05T14:00:00Z",
            },
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["bySession"], [])


    def test_day_groups_trades_by_utc_day_of_week(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},  # Monday
            {"id": "2", "timestamp": "2026-01-05T14:00:00Z"},  # Monday
            {"id": "3", "timestamp": "2026-01-06T10:00:00Z"},  # Tuesday
            {"id": "4", "timestamp": "2026-01-09T10:00:00Z"},  # Friday
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byDay"], [
            {"day": "Monday", "count": 2},
            {"day": "Tuesday", "count": 1},
            {"day": "Friday", "count": 1},
        ])

    def test_day_normalizes_offset_timestamps_to_utc(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T00:30:00+01:00"},
            {"id": "2", "timestamp": "2026-01-05T00:30:00-04:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byDay"], [
            {"day": "Monday", "count": 1},
            {"day": "Sunday", "count": 1},
        ])

    def test_day_excludes_invalid_and_missing_timestamps(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},
            {"id": "2", "timestamp": "not-a-timestamp"},
            {"id": "3"},
            {"id": "4", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byDay"], [
            {"day": "Monday", "count": 1},
        ])

    def test_day_returns_empty_when_no_valid_timestamps_exist(self):
        trades = [
            {"id": "1", "timestamp": "invalid"},
            {"id": "2"},
            {"id": "3", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byDay"], [])


    def test_week_groups_trades_by_iso_calendar_week(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},  # ISO week 2
            {"id": "2", "timestamp": "2026-01-06T14:00:00Z"},  # ISO week 2
            {"id": "3", "timestamp": "2026-01-12T10:00:00Z"},  # ISO week 3
            {"id": "4", "timestamp": "2026-01-19T10:00:00Z"},  # ISO week 4
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byWeek"], [
            {"year": 2026, "week": 2, "count": 2},
            {"year": 2026, "week": 3, "count": 1},
            {"year": 2026, "week": 4, "count": 1},
        ])

    def test_week_uses_iso_year_at_new_year_boundary(self):
        trades = [
            {"id": "1", "timestamp": "2025-12-29T12:00:00Z"},  # ISO 2026-W01
            {"id": "2", "timestamp": "2026-01-01T12:00:00Z"},  # ISO 2026-W01
            {"id": "3", "timestamp": "2026-01-05T12:00:00Z"},  # ISO 2026-W02
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byWeek"], [
            {"year": 2026, "week": 1, "count": 2},
            {"year": 2026, "week": 2, "count": 1},
        ])

    def test_week_normalizes_offset_timestamps_to_utc(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-04T23:30:00-01:00"},  # Monday UTC, W02
            {"id": "2", "timestamp": "2026-01-04T22:30:00-02:00"},  # Monday UTC, W02
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byWeek"], [
            {"year": 2026, "week": 2, "count": 2},
        ])

    def test_week_excludes_invalid_and_missing_timestamps(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},
            {"id": "2", "timestamp": "not-a-timestamp"},
            {"id": "3"},
            {"id": "4", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byWeek"], [
            {"year": 2026, "week": 2, "count": 1},
        ])

    def test_week_returns_empty_when_no_valid_timestamps_exist(self):
        trades = [
            {"id": "1", "timestamp": "invalid"},
            {"id": "2"},
            {"id": "3", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byWeek"], [])


    def test_month_groups_trades_by_calendar_year_and_month(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},
            {"id": "2", "timestamp": "2026-01-20T14:00:00Z"},
            {"id": "3", "timestamp": "2026-02-01T10:00:00Z"},
            {"id": "4", "timestamp": "2026-03-15T10:00:00Z"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byMonth"], [
            {"year": 2026, "month": 1, "count": 2},
            {"year": 2026, "month": 2, "count": 1},
            {"year": 2026, "month": 3, "count": 1},
        ])

    def test_month_keeps_same_month_separate_across_years(self):
        trades = [
            {"id": "1", "timestamp": "2025-01-15T12:00:00Z"},
            {"id": "2", "timestamp": "2026-01-15T12:00:00Z"},
            {"id": "3", "timestamp": "2027-01-15T12:00:00Z"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byMonth"], [
            {"year": 2025, "month": 1, "count": 1},
            {"year": 2026, "month": 1, "count": 1},
            {"year": 2027, "month": 1, "count": 1},
        ])

    def test_month_normalizes_offset_timestamps_to_utc(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-31T23:30:00-01:00"},
            {"id": "2", "timestamp": "2026-02-01T00:30:00+00:00"},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byMonth"], [
            {"year": 2026, "month": 2, "count": 2},
        ])

    def test_month_excludes_invalid_and_missing_timestamps(self):
        trades = [
            {"id": "1", "timestamp": "2026-01-05T09:00:00Z"},
            {"id": "2", "timestamp": "not-a-timestamp"},
            {"id": "3"},
            {"id": "4", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byMonth"], [
            {"year": 2026, "month": 1, "count": 1},
        ])

    def test_month_returns_empty_when_no_valid_timestamps_exist(self):
        trades = [
            {"id": "1", "timestamp": "invalid"},
            {"id": "2"},
            {"id": "3", "timestamp": ""},
        ]

        stats = calculate_journal_analytics(trades)

        self.assertEqual(stats["byMonth"], [])


if __name__ == "__main__":
    unittest.main()

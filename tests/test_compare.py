from services.compare import compare_periods, select_periods


def _trade(
    trade_id,
    day,
    result="WIN",
    direction="LONG",
    entry=100,
    stop_loss=90,
    exit_price=110,
):
    return {
        "id": trade_id,
        "timestamp": f"2026-01-{day:02d}T10:00:00Z",
        "result": result,
        "direction": direction,
        "entry": entry,
        "stopLoss": stop_loss,
        "exitPrice": exit_price,
    }


def test_select_periods_are_chronological_and_non_overlapping():
    trades = [
        _trade(str(i), i, result="WIN" if i % 2 else "LOSS")
        for i in range(1, 11)
    ]

    current, previous = select_periods(
        trades,
        current_count=3,
        previous_count=4,
    )

    assert [trade["id"] for trade in previous] == ["4", "5", "6", "7"]
    assert [trade["id"] for trade in current] == ["8", "9", "10"]
    assert set(trade["id"] for trade in current).isdisjoint(
        trade["id"] for trade in previous
    )


def test_period_sizes_are_validated():
    trades = [_trade("1", 1)]

    for current_count, previous_count in ((0, 1), (1, 0)):
        try:
            select_periods(
                trades,
                current_count=current_count,
                previous_count=previous_count,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError for invalid period size")


def test_compare_calculates_performance_change():
    trades = [
        {
            **_trade("1", 1, result="LOSS", exit_price=95),
            "intelligence": {
                "calculated": {
                    "features": {
                        "actualR": -0.5,
                    }
                }
            },
        },
        {
            **_trade("2", 2, result="WIN", exit_price=120),
            "intelligence": {
                "calculated": {
                    "features": {
                        "actualR": 2.0,
                    }
                }
            },
        },
        {
            **_trade(
                "3",
                3,
                result="WIN",
                direction="SHORT",
                entry=100,
                stop_loss=110,
                exit_price=90,
            ),
            "intelligence": {
                "calculated": {
                    "features": {
                        "actualR": 1.0,
                    }
                }
            },
        },
        {
            **_trade(
                "4",
                4,
                result="LOSS",
                direction="SHORT",
                entry=100,
                stop_loss=110,
                exit_price=105,
            ),
            "intelligence": {
                "calculated": {
                    "features": {
                        "actualR": -0.5,
                    }
                }
            },
        },
    ]

    result = compare_periods(
        trades,
        current_count=2,
        previous_count=2,
    )

    assert result["version"] == 1
    assert result["periods"]["previous"]["tradeIds"] == ["1", "2"]
    assert result["periods"]["current"]["tradeIds"] == ["3", "4"]

    assert result["performance"]["winRate"]["previous"] == 0.5
    assert result["performance"]["winRate"]["current"] == 0.5

    assert result["performance"]["averageR"]["previous"] is not None
    assert result["performance"]["averageR"]["current"] is not None


def test_missing_actual_r_remains_missing():
    trades = [
        {
            "id": "1",
            "timestamp": "2026-01-01T10:00:00Z",
            "result": "WIN",
        },
        {
            "id": "2",
            "timestamp": "2026-01-02T10:00:00Z",
            "result": "LOSS",
        },
    ]

    result = compare_periods(
        trades,
        current_count=1,
        previous_count=1,
    )

    assert result["performance"]["actualR"]["current"]["average"] is None
    assert result["performance"]["actualR"]["current"]["coverage"] == 0.0
    assert result["performance"]["actualR"]["previous"]["average"] is None
    assert result["performance"]["actualR"]["previous"]["coverage"] == 0.0


def test_distribution_comparison_includes_supporting_trade_ids():
    trades = [
        {
            **_trade("1", 1, result="WIN"),
            "setup": "BREAKOUT",
            "session": "LONDON",
        },
        {
            **_trade("2", 2, result="LOSS"),
            "setup": "REVERSAL",
            "session": "NEW_YORK",
        },
        {
            **_trade("3", 3, result="WIN"),
            "setup": "BREAKOUT",
            "session": "LONDON",
        },
        {
            **_trade("4", 4, result="LOSS"),
            "setup": "BREAKOUT",
            "session": "LONDON",
        },
    ]

    result = compare_periods(
        trades,
        current_count=2,
        previous_count=2,
    )

    setup_values = {
        item["value"]: item
        for item in result["distributions"]["setup"]["values"]
    }

    assert setup_values["BREAKOUT"]["previous"]["count"] == 1
    assert setup_values["BREAKOUT"]["previous"]["tradeIds"] == ["1"]

    assert setup_values["BREAKOUT"]["current"]["count"] == 2
    assert setup_values["BREAKOUT"]["current"]["tradeIds"] == ["3", "4"]

    assert setup_values["BREAKOUT"]["percentagePointChange"] == 0.5


def test_insufficient_history_does_not_fabricate_previous_trades():
    trades = [
        _trade("1", 1),
        _trade("2", 2),
    ]

    result = compare_periods(
        trades,
        current_count=5,
        previous_count=5,
    )

    assert result["periods"]["current"]["actualCount"] == 2
    assert result["periods"]["previous"]["actualCount"] == 0
    assert result["periods"]["previous"]["tradeIds"] == []

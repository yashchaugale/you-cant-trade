from services.edge_map import build_edge_map


def make_trade(
    trade_id,
    setup,
    regime,
    result,
    actual_r=None,
):
    trade = {
        "id": trade_id,
        "setup": setup,
        "result": result,
        "intelligence": {
            "marketContext": {
                "regime": regime,
            },
        },
    }

    if actual_r is not None:
        trade["intelligence"]["calculated"] = {
            "features": {
                "actualR": actual_r,
            },
        }

    return trade


def test_setup_regime_creates_separate_cells():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
        make_trade("4", "Breakout", "CONTRACTING", "WIN", 2.0),
        make_trade("5", "Breakout", "CONTRACTING", "LOSS", -1.0),
        make_trade("6", "Breakout", "CONTRACTING", "LOSS", -0.5),
    ]

    cells = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )

    assert len(cells) == 2
    assert {
        (cell["valueA"], cell["valueB"])
        for cell in cells
    } == {
        ("Breakout", "EXPANDING"),
        ("Breakout", "CONTRACTING"),
    }


def test_setup_regime_calculates_sample_and_win_rate():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
    ]

    cells = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )

    cell = cells[0]

    assert cell["sampleSize"] == 3
    assert cell["outcomes"] == {
        "wins": 2,
        "losses": 1,
        "breakEven": 0,
    }
    assert cell["winRate"] == 0.666667


def test_setup_regime_calculates_average_r_and_expectancy():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )[0]

    assert cell["averageR"] == 0.5
    assert cell["expectancy"] == 0.5


def test_setup_regime_does_not_fabricate_missing_actual_r():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN"),
        make_trade("2", "Breakout", "EXPANDING", "LOSS"),
        make_trade("3", "Breakout", "EXPANDING", "WIN"),
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )[0]

    assert cell["averageR"] is None
    assert cell["expectancy"] is None
    assert cell["evidenceStrength"]["actualRCoverage"] == 0.0


def test_setup_regime_enforces_minimum_sample():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.0),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
    ]

    cells = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )

    assert cells == []


def test_setup_regime_reports_evidence_strength():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )[0]

    assert cell["evidenceStrength"] == {
        "sampleSize": 3,
        "actualRCoverage": 1.0,
        "level": "LOW",
        "minimumSample": 3,
    }


def test_setup_regime_returns_supporting_trade_ids():
    trades = [
        make_trade("trade-1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("trade-2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("trade-3", "Breakout", "EXPANDING", "WIN", 1.0),
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )[0]

    assert cell["sourceTradeIds"] == [
        "trade-1",
        "trade-2",
        "trade-3",
    ]


def test_setup_regime_supports_regime_objects():
    trades = [
        make_trade(
            "1",
            "Breakout",
            {
                "regime": "EXPANDING",
                "confidence": 1,
            },
            "WIN",
            1.5,
        ),
        make_trade(
            "2",
            "Breakout",
            {
                "regime": "EXPANDING",
                "confidence": 1,
            },
            "LOSS",
            -1.0,
        ),
        make_trade(
            "3",
            "Breakout",
            {
                "regime": "EXPANDING",
                "confidence": 1,
            },
            "WIN",
            1.0,
        ),
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )[0]

    assert cell["valueA"] == "Breakout"
    assert cell["valueB"] == "EXPANDING"


def test_setup_regime_excludes_unreviewed_trades():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
        make_trade("4", "Breakout", "EXPANDING", None, 2.0),
    ]

    cells = build_edge_map(
        trades,
        "setup",
        "market_regime",
    )

    cell = cells[0]

    assert cell["sampleSize"] == 3
    assert cell["sourceTradeIds"] == ["1", "2", "3"]


def test_setup_session_creates_separate_cells():
    trades = [
        make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
        make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
        make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
    ]

    for trade in trades:
        trade["session"] = "LONDON"

    trades.extend([
        {
            **make_trade("4", "Breakout", "EXPANDING", "WIN", 2.0),
            "session": "NEW_YORK",
        },
        {
            **make_trade("5", "Breakout", "EXPANDING", "LOSS", -1.0),
            "session": "NEW_YORK",
        },
        {
            **make_trade("6", "Breakout", "EXPANDING", "WIN", 1.0),
            "session": "NEW_YORK",
        },
    ])

    cells = build_edge_map(
        trades,
        "setup",
        "session",
    )

    assert len(cells) == 2
    assert {
        (cell["valueA"], cell["valueB"])
        for cell in cells
    } == {
        ("Breakout", "LONDON"),
        ("Breakout", "NEW_YORK"),
    }


def test_setup_session_calculates_metrics():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
            "session": "LONDON",
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "session": "LONDON",
        },
        {
            **make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
            "session": "LONDON",
        },
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "session",
    )[0]

    assert cell["sampleSize"] == 3
    assert cell["winRate"] == 0.666667
    assert cell["averageR"] == 0.5
    assert cell["expectancy"] == 0.5
    assert cell["evidenceStrength"]["actualRCoverage"] == 1.0


def test_setup_session_returns_supporting_trade_ids():
    trades = [
        {
            **make_trade("trade-1", "Breakout", "EXPANDING", "WIN", 1.5),
            "session": "LONDON",
        },
        {
            **make_trade("trade-2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "session": "LONDON",
        },
        {
            **make_trade("trade-3", "Breakout", "EXPANDING", "WIN", 1.0),
            "session": "LONDON",
        },
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "session",
    )[0]

    assert cell["sourceTradeIds"] == [
        "trade-1",
        "trade-2",
        "trade-3",
    ]


def test_setup_session_enforces_minimum_sample():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.0),
            "session": "LONDON",
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "session": "LONDON",
        },
    ]

    assert build_edge_map(
        trades,
        "setup",
        "session",
    ) == []


def test_setup_direction_creates_separate_cells():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
            "direction": "LONG",
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "direction": "LONG",
        },
        {
            **make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
            "direction": "LONG",
        },
        {
            **make_trade("4", "Breakout", "EXPANDING", "WIN", 2.0),
            "direction": "SHORT",
        },
        {
            **make_trade("5", "Breakout", "EXPANDING", "LOSS", -1.0),
            "direction": "SHORT",
        },
        {
            **make_trade("6", "Breakout", "EXPANDING", "WIN", 1.0),
            "direction": "SHORT",
        },
    ]

    cells = build_edge_map(
        trades,
        "setup",
        "direction",
    )

    assert len(cells) == 2
    assert {
        (cell["valueA"], cell["valueB"])
        for cell in cells
    } == {
        ("Breakout", "LONG"),
        ("Breakout", "SHORT"),
    }


def test_setup_direction_calculates_metrics():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
            "direction": "LONG",
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "direction": "LONG",
        },
        {
            **make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
            "direction": "LONG",
        },
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "direction",
    )[0]

    assert cell["sampleSize"] == 3
    assert cell["winRate"] == 0.666667
    assert cell["averageR"] == 0.5
    assert cell["expectancy"] == 0.5
    assert cell["evidenceStrength"]["actualRCoverage"] == 1.0


def test_setup_direction_returns_supporting_trade_ids():
    trades = [
        {
            **make_trade("trade-1", "Breakout", "EXPANDING", "WIN", 1.5),
            "direction": "LONG",
        },
        {
            **make_trade("trade-2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "direction": "LONG",
        },
        {
            **make_trade("trade-3", "Breakout", "EXPANDING", "WIN", 1.0),
            "direction": "LONG",
        },
    ]

    cell = build_edge_map(
        trades,
        "setup",
        "direction",
    )[0]

    assert cell["sourceTradeIds"] == [
        "trade-1",
        "trade-2",
        "trade-3",
    ]


def test_setup_direction_enforces_minimum_sample():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.0),
            "direction": "LONG",
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "direction": "LONG",
        },
    ]

    assert build_edge_map(
        trades,
        "setup",
        "direction",
    ) == []


def test_structure_setup_creates_separate_cells():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("4", "Breakout", "EXPANDING", "WIN", 2.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "RANGING"},
            },
        },
        {
            **make_trade("5", "Breakout", "EXPANDING", "LOSS", -1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "RANGING"},
            },
        },
        {
            **make_trade("6", "Breakout", "EXPANDING", "WIN", 1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "RANGING"},
            },
        },
    ]

    cells = build_edge_map(
        trades,
        "structure_state",
        "setup",
    )

    assert len(cells) == 2
    assert {
        (cell["valueA"], cell["valueB"])
        for cell in cells
    } == {
        ("TRENDING", "Breakout"),
        ("RANGING", "Breakout"),
    }


def test_structure_setup_calculates_metrics():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.5),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
                "calculated": {"features": {"actualR": 1.5}},
            },
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
                "calculated": {"features": {"actualR": -1.0}},
            },
        },
        {
            **make_trade("3", "Breakout", "EXPANDING", "WIN", 1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
                "calculated": {"features": {"actualR": 1.0}},
            },
        },
    ]

    cell = build_edge_map(
        trades,
        "structure_state",
        "setup",
    )[0]

    assert cell["sampleSize"] == 3
    assert cell["winRate"] == 0.666667
    assert cell["averageR"] == 0.5
    assert cell["expectancy"] == 0.5
    assert cell["evidenceStrength"]["actualRCoverage"] == 1.0

def test_structure_setup_returns_supporting_trade_ids():
    trades = [
        {
            **make_trade("trade-1", "Breakout", "EXPANDING", "WIN", 1.5),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("trade-2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("trade-3", "Breakout", "EXPANDING", "WIN", 1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
    ]

    cell = build_edge_map(
        trades,
        "structure_state",
        "setup",
    )[0]

    assert cell["sourceTradeIds"] == [
        "trade-1",
        "trade-2",
        "trade-3",
    ]


def test_structure_setup_enforces_minimum_sample():
    trades = [
        {
            **make_trade("1", "Breakout", "EXPANDING", "WIN", 1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
        {
            **make_trade("2", "Breakout", "EXPANDING", "LOSS", -1.0),
            "intelligence": {
                "marketContext": {"regime": "EXPANDING"},
                "marketStructure": {"state": "TRENDING"},
            },
        },
    ]

    assert build_edge_map(
        trades,
        "structure_state",
        "setup",
    ) == []

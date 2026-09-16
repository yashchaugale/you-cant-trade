# You Can't Trade — Target Architecture

## Principles

1. The canonical trade record and deterministic calculations are authoritative.
2. AI is an optional interpretation layer and can never block capture.
3. Provider changes must not change the domain trade contract.
4. Evidence and unknowns must be traceable to records and calculations.
5. Local mode is the default personal privacy boundary.

## Target flow

```text
TradingView extension
  → canonical capture + screenshot
  → storage provider
  → deterministic intelligence
  → retrieval/pattern/memory systems
  → optional evidence-packet AI
  → case file, review, experiments
```

## Layers

- **Capture layer:** explicit TradingView action, page/content bridge, screenshot and RR metadata.
- **Domain layer:** schema-versioned trade, review, intelligence, memory, experiment, and evidence contracts.
- **Deterministic intelligence:** calculations, market context, structure, outcomes, historical aggregation, pattern validation, data health.
- **Persistence:** local SQLite/filesystem first; Notion opt-in; future hosted Postgres adapter only for a public edition.
- **Retrieval:** bounded, relevant historical evidence; never send an uncontrolled whole database to a model.
- **AI:** provider adapter, structured evidence packet, strict output validation, provenance and freshness.
- **Presentation:** Home, Trades, Explore, Review, Memory, Experiments, Import, Settings.

## Phase 3 — Deterministic trading intelligence

Phase 3 establishes the deterministic measurement layer that turns canonical trades into evidence about trading performance.

### Analytics coverage

The deterministic analytics layer calculates:

- Core outcomes: win rate, average R, median R, expectancy, profit factor, average winner, average loser, biggest winner, biggest loser, drawdown, and win/loss streaks.
- Time breakdowns: hour, session, day, ISO week, month, and holding duration.
- Setup breakdowns: sample size, win rate, average R, expectancy, and recent/historical performance where supported.
- Context breakdowns: market regime, structure, direction, session, and supported volatility.
- Data health: missing fields, incomplete trades, missing setup/execution information, missing screenshots, and evidence quality.

### Evidence and traceability

Analytics use the strongest available evidence for each calculation. Missing evidence is excluded from the calculation that requires it rather than being treated as negative performance.

Important analytics expose source trade IDs for traceability. Group-level IDs correspond to the canonical trades contributing to that group; Actual R metrics share the exact Actual R trade population; chronological metrics preserve the ordering used by their calculations.

Traceability does not alter the underlying calculation. Records without canonical trade IDs remain analyzable where their required fields are present, but cannot be represented in source-ID traceability lists.

All deterministic calculations are provider-neutral, reproducible, and covered by automated tests, including datasets of up to 1,000 trades.

## Current-to-target map

Current extension, FastAPI loopback service, SQLite provider, Notion provider, schema v4 intelligence namespace, deterministic analytics, similarity, pattern discovery, data health, experiments, and AI provider abstraction are foundations. Edge/Leak Maps, memory lifecycle, import system, target navigation, and packaging remain planned.

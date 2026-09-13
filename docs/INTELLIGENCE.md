# Deterministic Intelligence Plan

## Already implemented

- Basic outcomes and actual-R analytics.
- Candle normalization and validation.
- Market statistics/regime components.
- Structure engines and temporal anchoring.
- Setup fingerprints.
- Canonical-context-first historical similarity.
- Basic sample-size warnings.

## Target statistics

Win rate, mean/median R, expectancy, profit factor, distribution, drawdown, consecutive results, time/session/day/week/month, setup, direction, structure, regime, volatility, and duration. Every statistic must expose its denominator and missing-data treatment.

### Evidence populations

Deterministic analytics must track the evidence population used by each metric rather than treating every trade as equally complete:

- `outcomeTrades`: trades with a recorded `WIN`, `LOSS`, or `BE` outcome.
- `plannedRTrades`: trades with calculable planned R from entry, stop loss, and take profit.
- `actualRTrades`: trades with a calculable realized Actual R from a known outcome, entry, stop loss, exit price, and valid direction.

Missing exit prices must not exclude a trade from outcome-based, planned-R, setup, context, or other analyses that do not require realized R. Actual-R metrics use only the `actualRTrades` population. Missing evidence is unknown, not negative performance.

## Pattern Discovery

Search setup, session, direction, structure, regime and bounded combinations. A finding requires sample size, baseline, difference from baseline, recency, stability, and evidence strength. Tiny samples, multiple-comparison effects, survivorship bias, and missing fields must produce warnings—not confident claims.

## Edge Map

Expose cells such as Setup × Regime and Setup × Session, with underlying trades and evidence. A cell is not an edge until its sample and stability thresholds are met.

## Leak Map

Only measured, supported behaviors become leaks: late entry, early exit, moved stop, rule violation, counter-structure trade, wrong session, overtrading, revenge tag, poor risk, or holding mismatch. Missing tags are unknown, never inferred as failure.

## Data Health

Report completeness of setup, execution, context, screenshot, result, and review fields, then explain which missing fields would improve a requested analysis.


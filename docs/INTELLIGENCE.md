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

Expectancy is calculated as the mean realized Actual R across `actualRTrades`. Its evidence count and WIN/LOSS/BE breakdown must use that same population. A missing exit price or invalid direction excludes a trade from expectancy, but does not exclude it from analyses that do not require realized R.

Profit factor is calculated as gross profit divided by gross loss across `actualRTrades`. Gross profit is the sum of positive realized Actual R values, while gross loss is the absolute sum of negative realized Actual R values. Break-even trades contribute zero and remain in the evidence count. If there is no gross loss, profit factor is `null` rather than infinity. Missing exit prices, invalid direction, zero-risk trades, and unknown outcomes are excluded from the Actual-R evidence population.

Average winner is calculated as the mean positive realized Actual R values across `actualRTrades`. Losses and break-even trades are excluded from the winner average. Its evidence count is the number of positive realized Actual R values. If there are no positive realized Actual R values, average winner is `null`.

Average loser is calculated as the mean negative realized Actual R values across `actualRTrades`. Wins and break-even trades are excluded from the loser average. Its evidence count is the number of negative realized Actual R values. If there are no negative realized Actual R values, average loser is `null`. The returned value remains negative to preserve the direction and magnitude of realized losses.

Biggest winner is the maximum positive realized Actual R value across `actualRTrades`. Losses and break-even trades are excluded. Its evidence count is the number of positive realized Actual R values. If there are no positive realized Actual R values, biggest winner is `null`.

Biggest loser is the minimum negative realized Actual R value across `actualRTrades`. Wins and break-even trades are excluded. Its evidence count is the number of negative realized Actual R values. If there are no negative realized Actual R values, biggest loser is `null`. The returned value remains negative to preserve the direction and magnitude of the largest realized loss.

Drawdown is the maximum observed peak-to-trough decline of the cumulative realized Actual R equity curve, using `actualRTrades` in chronological trade order. At each valid Actual-R observation, cumulative realized R is compared with the highest equity reached so far. Drawdown is returned as a positive magnitude. Trades without calculable Actual R are excluded from the equity curve. Its evidence count is the number of chronological Actual-R observations used. If there are no observed peak-to-trough declines, drawdown is `0`.

Win streak is the maximum number of consecutive `WIN` outcomes in chronological trade order. `LOSS`, `BE`, and unknown or missing outcomes break the current win streak but are not counted as wins. Its evidence count is the number of trades considered in the chronological outcome sequence. If there are no wins, win streak is `0`.

Loss streak is the maximum number of consecutive `LOSS` outcomes in chronological trade order. `WIN`, `BE`, and unknown or missing outcomes break the current loss streak but are not counted as losses. Its evidence count is the number of trades considered in the chronological outcome sequence. If there are no losses, loss streak is `0`.

Hour analysis groups trades by the UTC hour extracted from each valid canonical trade timestamp. Offset-aware timestamps are normalized to UTC before the hour is determined. Invalid or missing timestamps are excluded. Results are returned as hour buckets from `0` through `23`, with each bucket exposing its trade count. No user-local timezone is inferred unless an explicit timezone is later configured.

Holding duration is an estimated chart-path duration calculated from `chartAnchorTime` to `outcomeEvidenceTime`. It represents the elapsed time from the captured chart anchor to the first observed candle that reached the planned stop or target; it is not actual broker or execution holding time. Durations are calculated only when both timestamps are valid numeric values and the resulting duration is positive. Missing, invalid, zero, or negative durations are treated as unknown and excluded. The analytics expose the average duration in seconds, median duration in seconds, and the number of valid duration observations.

Missing exit prices must not exclude a trade from outcome-based, planned-R, setup, context, or other analyses that do not require realized R. Actual-R metrics use only the `actualRTrades` population. Missing evidence is unknown, not negative performance.

## Pattern Discovery

Search setup, session, direction, structure, regime and bounded combinations. A finding requires sample size, baseline, difference from baseline, recency, stability, and evidence strength. Tiny samples, multiple-comparison effects, survivorship bias, and missing fields must produce warnings—not confident claims.

## Edge Map

Expose cells such as Setup × Regime and Setup × Session, with underlying trades and evidence. A cell is not an edge until its sample and stability thresholds are met.

## Leak Map

Only measured, supported behaviors become leaks: late entry, early exit, moved stop, rule violation, counter-structure trade, wrong session, overtrading, revenge tag, poor risk, or holding mismatch. Missing tags are unknown, never inferred as failure.

## Data Health

Report completeness of setup, execution, context, screenshot, result, and review fields, then explain which missing fields would improve a requested analysis.


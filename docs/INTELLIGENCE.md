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

### Setup performance

Setup performance groups canonical trades by their recorded setup name. A setup must be a non-empty string after trimming whitespace; missing, empty, and non-string setup values are excluded. Setup sample size counts every trade with a valid setup, regardless of outcome or review completeness.

Per-setup win rate is `WIN / (WIN + LOSS)`. Break-even and unknown outcomes are excluded from the denominator. If a setup has no decided WIN/LOSS trades, its win rate is `null`.

Per-setup average R and expectancy use the same realized Actual-R evidence rules as the global metrics: only trades with valid entry, stop loss, exit price, direction, and non-zero risk contribute. Missing or invalid Actual-R evidence is excluded from those calculations without reducing the setup's overall sample size. Expectancy is the mean realized Actual R for that setup.

Recent setup performance uses the 10 most recent trades for each setup, ordered by canonical trade timestamp descending. If fewer than 10 trades exist, all available setup trades are used. Its sample size counts all trades in that recent window, while its win rate uses only WIN/LOSS outcomes.

Historical setup performance represents the full available history for that setup with no arbitrary lookback. It exposes the full-history sample size, win rate, average R, and expectancy using the same deterministic evidence rules as setup performance. Recent and historical results are descriptive measurements only and must not be treated as predictions.

### Market regime performance

Market regime performance groups trades by the canonical `marketContext.regime` generated by the existing market-regime intelligence. Recognized regimes are `TRENDING`, `RANGING`, `EXPANDING`, `CONTRACTING`, and `UNCERTAIN`. Missing or unrecognized regime values are excluded; missing regime information is not treated as `UNCERTAIN`.

For each recognized regime, sample size counts every trade assigned to that regime. Win rate is `WIN / (WIN + LOSS)`, with break-even and unknown outcomes excluded from the denominator. Average R and expectancy use only valid realized Actual-R evidence and do not reduce the regime's overall sample size when Actual-R evidence is missing.

Results use deterministic ordering: `TRENDING`, `RANGING`, `EXPANDING`, `CONTRACTING`, then `UNCERTAIN`. Regime performance is descriptive evidence about observed trades and must not be treated as predictive.

### Direction performance

Direction performance groups trades by the canonical `direction` field. Recognized directions are `LONG` and `SHORT`. Missing or unrecognized direction values are treated as unknown evidence and excluded.

For each recognized direction, sample size counts every trade with that valid direction. Win rate is `WIN / (WIN + LOSS)`, with break-even and unknown outcomes excluded from the denominator. If a direction has no decided WIN/LOSS trades, its win rate is `null`.

Average R and expectancy use only valid realized Actual-R evidence using the same global rules: valid entry, stop loss, exit price, direction, and non-zero risk. Missing or invalid Actual-R evidence does not reduce the direction's overall sample size.

Results use deterministic ordering: `LONG`, then `SHORT`. Direction performance is descriptive evidence about observed trades and must not be treated as predictive.

### Volatility performance

Volatility performance groups trades by the canonical volatility state derived from the persisted `marketContext.statistics.volatility.rangeRatio`. The existing market-intelligence thresholds are used deterministically: `rangeRatio >= 1.5` is `EXPANDING`, `rangeRatio <= 0.67` is `CONTRACTING`, and values between those thresholds are `NORMAL`. Missing or invalid `rangeRatio` values are treated as unknown evidence and excluded.

For each recognized volatility state, sample size counts every trade with valid volatility evidence. Win rate is `WIN / (WIN + LOSS)`, with break-even and unknown outcomes excluded from the denominator. If a volatility state has no decided WIN/LOSS trades, its win rate is `null`.

Average R and expectancy use only valid realized Actual-R evidence using the same global rules: valid entry, stop loss, exit price, direction, and non-zero risk. Missing or invalid Actual-R evidence does not reduce the volatility state's overall sample size.

Results use deterministic ordering: `EXPANDING`, `NORMAL`, then `CONTRACTING`. Volatility performance is descriptive evidence about observed trades and must not be treated as predictive.

### Structure performance

Structure performance groups trades by the canonical `intelligence.marketStructure.state` produced by the existing You Can't Trade structure engine. Recognized structure states are `BULLISH` and `BEARISH`. Missing, `UNKNOWN`, and unrecognized structure states are treated as unknown evidence and excluded; unknown structure is never interpreted as bullish or bearish.

For each recognized structure state, sample size counts every trade assigned to that state. Win rate is `WIN / (WIN + LOSS)`, with break-even and unknown outcomes excluded from the denominator. If a structure state has no decided WIN/LOSS trades, its win rate is `null`.

Average R and expectancy use only valid realized Actual-R evidence using the same global rules: valid entry, stop loss, exit price, direction, and non-zero risk. Missing or invalid Actual-R evidence does not reduce the structure state's overall sample size.

Results use deterministic ordering: `BULLISH`, then `BEARISH`. Structure performance is descriptive evidence about observed trades and must not be treated as predictive.


## Pattern Discovery

Search setup, session, direction, structure, regime and bounded combinations. A finding requires sample size, baseline, difference from baseline, recency, stability, and evidence strength. Tiny samples, multiple-comparison effects, survivorship bias, and missing fields must produce warnings—not confident claims.

## Edge Map

Expose cells such as Setup × Regime and Setup × Session, with underlying trades and evidence. A cell is not an edge until its sample and stability thresholds are met.

## Leak Map

Only measured, supported behaviors become leaks: late entry, early exit, moved stop, rule violation, counter-structure trade, wrong session, overtrading, revenge tag, poor risk, or holding mismatch. Missing tags are unknown, never inferred as failure.

## Data Health

Report completeness of setup, execution, context, screenshot, result, and review fields, then explain which missing fields would improve a requested analysis.

### Incomplete trades

A trade is incomplete when one or more core capture fields are missing: symbol, timeframe, direction, entry, stop loss, take profit, or outcome. Each trade is counted once regardless of how many required fields are missing.

Reviewed exit price, Actual R, setup, session, market intelligence, and screenshot evidence are not required for the core incomplete-trade classification. Those dimensions are measured separately by their corresponding Data Health checks. An incomplete trade is a data-completeness finding, not a negative performance result.

### Missing execution information

Execution completeness is measured separately from core trade-capture completeness. A trade has execution evidence when at least one structured execution field is recorded, including actual entry, actual stop loss, actual take profit, entry or exit time, stop or target movement, partial exits, break-even, or slippage.

An empty execution object is treated as missing execution evidence. Exit price and Actual R are measured separately and are not required to establish execution evidence. Missing execution information is an evidence-quality finding, not a negative performance result.

### Missing screenshot information

Screenshot completeness is measured from the canonical screenshot evidence available on a trade. A screenshot is present when either the inline `screenshot` value or persisted `screenshotPath` is recorded.

Missing both forms of screenshot evidence is counted as missing screenshot information. Screenshot availability is an evidence-quality measurement and does not determine whether a trade is complete or profitable.

### Evidence quality

Evidence quality is reported as deterministic evidence coverage across six journal dimensions:

1. Outcome
2. Screenshot
3. Execution
4. Market context
5. Market structure
6. Setup fingerprint

For each canonical trade, each dimension contributes one evidence opportunity. A dimension is available when its corresponding deterministic Data Health evidence is present; otherwise it is treated as unknown.

The aggregate report exposes:

- `availableDimensions`: number of available evidence dimensions across all trades
- `totalDimensions`: total evidence opportunities (`trade count × 6`)
- `coverageRate`: available evidence divided by total evidence opportunities

An empty journal reports `coverageRate: null` because there are no evidence opportunities.

Evidence coverage is a data-quality measurement only. Missing evidence is unknown and is never treated as negative trading performance.

### Missing fields

Missing-field counts are deterministic completeness measurements across canonical trades. Core fields tracked include outcome, symbol, timeframe, direction, entry, stop loss, take profit, reviewed exit price, reviewed Actual R, setup, session, market context, market structure, and setup fingerprint.

Missing values are counted as unknown evidence and are never treated as negative trading performance. Reviewed-only fields such as exit price and Actual R are evaluated against reviewed trades, while core capture and review fields are counted according to their canonical trade population. Optional notes and emotions are not treated as required fields.


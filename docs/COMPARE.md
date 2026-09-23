# Compare — Definition Contract

## Purpose

The Compare system provides a deterministic historical comparison of two
non-overlapping trade periods.

It answers:

> What changed in my trading?

Compare is descriptive only.

It measures differences between historical trade sets. It does not predict
future performance, infer causes, rank periods, or make judgments about
whether a change is good or bad.

---

## 1. Period Model

Compare uses two chronological, non-overlapping trade periods:

### Current Period

The most recent N trades.

### Previous Period

The N trades immediately preceding the Current Period.

Example:

- Current Period: Last 30 trades
- Previous Period: Previous 100 trades

The periods must not overlap.

Trades are ordered chronologically using the canonical trade timestamp.

The comparison engine must use the same ordering deterministically for every
request.

---

## 2. Sample Size

Every comparison response exposes:

- current sample size
- previous sample size

A requested period may contain fewer trades than requested when insufficient
historical trades exist.

The system must never fabricate missing trades.

Small samples remain visible and must not be presented as statistically
reliable conclusions.

---

## 3. Performance Metrics

Both periods use identical deterministic calculations.

Compare:

- Win rate
- Expectancy
- Average R
- Actual R coverage
- Sample size

### Win Rate

Win rate is calculated from trades with a determinable outcome:

wins / (wins + losses)

Trades without a determinable win/loss outcome are excluded from the win-rate
denominator.

### Actual R

Actual R uses the existing canonical deterministic Actual-R calculation.

It requires sufficient entry, stop-loss, exit-price, and direction data.

Missing Actual R remains missing.

### Average R

Average R is the arithmetic mean of valid Actual R values.

### Expectancy

Compare reuses the existing deterministic expectancy definition.

The current system defines expectancy as the average realized R for the
available Actual R sample.

### Actual R Coverage

Actual R coverage is:

valid Actual R trades / period trade count

Coverage must be exposed alongside Average R and Expectancy.

A difference in Average R or Expectancy must never hide the underlying R
coverage.

---

## 4. Distribution Comparisons

Compare supports these distributions:

- Setup
- Session
- Direction
- Behavior
- Execution

For every category/value pair, expose:

- current count
- current percentage
- previous count
- previous percentage
- percentage-point difference
- supporting current trade IDs
- supporting previous trade IDs

Unknown or missing values remain unknown.

The system must not infer a category from unrelated fields.

---

## 5. Setup

Setup distribution uses the existing canonical setup value used by the
journal analytics system.

It must not introduce a second setup taxonomy.

---

## 6. Session

Session distribution uses the existing canonical session field.

Supported session values are the existing canonical values:

- ASIA
- LONDON
- NEW_YORK
- OTHER

Missing session values remain missing.

---

## 7. Direction

Direction distribution uses the existing canonical direction field.

Supported values are the existing canonical directional values:

- LONG
- SHORT

Missing direction values remain missing.

---

## 8. Behavior

Behavior comparison uses explicitly recorded canonical behavior information.

Behavior must not be inferred from trade outcome.

A behavior category is included only when supported by recorded canonical
behavior evidence.

---

## 9. Execution

Execution comparison uses the existing explicit execution tag.

Execution categories must not be inferred from outcome, R, or other
performance measurements.

Missing execution tags remain missing.

---

## 10. Change Calculation

For numeric performance metrics:

change = current value - previous value

For distribution percentages:

percentage-point change =
current percentage - previous percentage

The comparison must preserve the sign and numeric difference.

The system may identify the largest measurable increase or decrease, but must
not label it as inherently good or bad.

---

## 11. Biggest Improvement / Biggest Decline

"Biggest improvement" and "biggest decline" are deterministic summaries of
the largest measurable changes.

They are not judgments about trading quality.

The comparison engine must define an explicit metric and ordering before
selecting a largest change.

If no defensible comparison exists, the result is UNKNOWN rather than an
invented conclusion.

---

## 12. Pattern Changes

Compare may identify:

### New Patterns

A pattern is new when:

- it is present in the Current Period
- it is absent from the Previous Period
- it satisfies the existing deterministic pattern-discovery minimum sample
  requirements

### Disappearing Patterns

A pattern is disappearing when:

- it is present in the Previous Period
- it is absent from the Current Period
- it satisfies the existing deterministic pattern-discovery minimum sample
  requirements

Pattern definitions must reuse the existing pattern-discovery taxonomy.

Compare must not create a second pattern taxonomy.

One-off observations that do not satisfy the existing pattern threshold are
not promoted to recurring patterns.

---

## 13. Supporting Trades

Every comparison result that can be traced to individual trades should expose
supporting trade IDs.

Supporting trades must remain traceable back to the original Trade Case
Files.

The comparison engine must not create synthetic trades.

---

## 14. Missing Evidence

Missing data is UNKNOWN.

Missing data must never be converted into:

- zero performance
- a negative result
- a positive result
- a behavioral classification
- a causal explanation

Coverage must be exposed where missing data affects a measurement.

---

## 15. Evidence and Sample Limitations

Compare describes historical observations only.

It must not claim:

- statistical significance unless explicitly implemented
- causality
- prediction
- future improvement
- future deterioration
- strategy superiority
- trader quality

Small samples must remain visible.

Low coverage must remain visible.

---

## 16. Determinism

Given the same canonical trade records and the same period parameters,
Compare must return the same result.

No AI call is required for comparison calculation.

AI may later explain an already-computed comparison, but AI is not
authoritative for:

- period membership
- metric calculation
- distribution counts
- pattern classification
- change calculation
- supporting trade selection

---

## 17. Output Contract

The comparison response should contain:

- version
- current period definition
- previous period definition
- current sample size
- previous sample size
- performance comparison
- distribution comparisons
- behavior comparison
- execution comparison
- biggest measurable increase
- biggest measurable decrease
- new patterns
- disappearing patterns
- supporting trade IDs

---

## 18. Phase 7 Completion Criterion

Phase 7 is complete when a user can select two historical periods and
deterministically see:

> What changed in my trading?

The result must remain descriptive, evidence-backed, traceable, and
consistent with the existing deterministic analytics and pattern-discovery
systems.

# Current Understanding Engine

## 1. Purpose

The Current Understanding Engine composes existing deterministic trading
analytics into a small, traceable snapshot of recorded trading evidence.

Its purpose is to describe what the available evidence currently supports.

It does not predict future performance, recommend trades, infer causality,
or use AI-generated evidence.

## 2. Architecture

The engine is implemented in `services/current_understanding.py`.

Its processing sequence is:

1. Validate and normalize the supplied inputs.
2. Select the current pattern observation and behavioral watch.
3. Format the recent performance comparison.
4. Build eligible findings from the available evidence.
5. Prevent the same pattern from appearing as both newly standing out
   and weakening in the same snapshot.
6. Verify findings and their evidence.
7. Prioritize findings deterministically.
8. Surface no more than three findings.
9. Assemble the final response.

The engine is a composition layer. It relies on upstream analytics
for the correctness of the evidence supplied to it.

## 3. Input contract

The public entry point is:

`build_current_understanding(...)`

It accepts keyword-only inputs:

| Input | Expected type | Purpose |
|---|---|---|
| `trade_count` | Non-negative integer | Number of recorded trades |
| `patterns` | List of dictionaries | Pattern observations and weakening-pattern evidence |
| `leaks` | List of dictionaries | Behavioral watch candidates |
| `compare` | Dictionary | Performance and behavioral comparison evidence |
| `data_health` | Dictionary | Aggregate data completeness evidence |

`trade_count` is required. Booleans, negative values, and non-integers
are rejected with `ValueError`.

Invalid optional collection types are normalized to empty or unavailable
inputs: patterns and leaks become empty lists, and invalid data health
becomes unavailable.

The engine does not independently retrieve trades or calculate the
upstream analytics represented by these inputs.

## 4. Output contract

The response contains:

| Field | Meaning |
|---|---|
| `version` | Output contract version |
| `status` | `NO_TRADES`, `LEARNING`, or `READY` |
| `tradeCount` | Supplied trade count |
| `observation` | Selected and formatted pattern observation, if available |
| `watch` | Selected and formatted behavioral watch, if available |
| `recentChange` | Formatted recent comparison, if available |
| `findings` | Verified, prioritized findings, limited to three |

### Status behavior

- `NO_TRADES`: returned when `trade_count` is zero. Observation, watch,
  and recent change are null. The response does not include findings.
- `LEARNING`: returned when trades exist but no qualifying observation
  is selected.
- `READY`: returned when a qualifying observation is selected.

`READY` indicates that an observation exists. It does not guarantee
that a finding exists or that all available evidence is complete.

## 5. Supported finding types

The engine supports six finding types:

| Finding type | Evidence source |
|---|---|
| `NEW_PATTERN` | Selected pattern observation |
| `PERFORMANCE_CHANGE` | Performance comparison |
| `BEHAVIOR_CHANGE` | Behavioral comparison |
| `WEAKENING_PATTERN` | Pattern history and weakening evidence |
| `INTERESTING_RELATIONSHIP` | Relationship comparison |
| `DATA_GAP` | Aggregate data health |

Each finding is built by a dedicated function. A finding is emitted only
when its builder's evidence requirements are satisfied.

Finding summaries describe observed evidence. They are not predictions
or causal explanations.

## 6. Evidence and validation

Before findings are surfaced, `_verify_findings()` checks their structure
and evidence.

The validation suite covers:

- Supported finding types and required identifiers.
- Duplicate finding identifiers.
- Sample-size consistency.
- Numeric metric types and non-finite values.
- Evidence structure and source consistency.
- Trade-ID validity, uniqueness, and traceability.
- Supporting trade-ID consistency.
- Finding status and text fields.

Individual builders also validate their own inputs, including sample
sizes, numeric values, evidence strength, and trade-ID consistency.

Malformed or unsupported findings are rejected rather than presented
as supported conclusions.

`DATA_GAP` uses aggregate data-health counts. It does not invent
trade-level identifiers when the source only provides aggregate counts.

## 7. Prioritization

Findings are ranked using this type priority:

1. `PERFORMANCE_CHANGE`
2. `WEAKENING_PATTERN`
3. `NEW_PATTERN`
4. `BEHAVIOR_CHANGE`
5. `INTERESTING_RELATIONSHIP`
6. `DATA_GAP`

Within a type, ordering uses sample size and finding identifier as
deterministic tie-breakers.

The engine assigns sequential priority numbers after sorting and
surfaces only the first three findings.

## 8. Determinism

For identical valid inputs, the engine is expected to produce identical
complete outputs.

Selection and ranking use deterministic ordering. Regression tests
cover reordered pattern, leak, and behavior candidates, as well as
identical complete inputs.

The engine does not depend on an LLM or an external AI provider.

## 9. Known limitations and non-goals

- The engine depends on upstream analytics and does not independently
  prove their correctness.
- Findings are limited to the six implemented types.
- Only three findings are surfaced in one snapshot.
- Aggregate data-health evidence cannot provide trade-level IDs that
  were not supplied by its source.
- Missing evidence is not proof of poor trading performance.
- Findings describe recorded history; they do not establish causality
  or predict future outcomes.
- The engine does not generate experiments, autonomously investigate
  hypotheses, or continuously learn from new trades.
- AI investigation and experiment workflows belong to later roadmap
  phases, not this deterministic engine.

## 10. Verification

At the Phase 2 documentation baseline:

- Focused Understanding Engine tests: 72 passed.
- Full pytest suite: 351 passed.
- One existing Starlette/httpx TestClient deprecation warning remains.
- No test failures were reported.

Relevant tests are in `tests/test_current_understanding.py`.

The tests cover finding builders, public output, prioritization,
validation, malformed inputs, evidence traceability, data gaps,
coexistence, and deterministic behavior.

## 11. Phase 2 completion boundary

Phase 2 establishes a deterministic, validated, traceable current
understanding snapshot from existing analytics.

It does not include AI investigation, experiment execution,
continuous memory, or broader autonomous workflows.

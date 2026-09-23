# Trading Memory Contract

**Version:** 1  
**Phase:** 8 — Trading Memory

## 1. Goal

Trading Memory preserves what the trader has learned from historical trading evidence.

Memory transforms deterministic observations into persistent, evidence-linked findings that can be revisited, challenged, rechecked, updated, and retired.

The core question is:

> What have I learned from my trading history, and is that finding still supported?

Memory is descriptive. It does not predict future outcomes, establish causation, or provide trading advice.

---

## 2. Core Memory Model

Every Memory finding consists of:

Finding
  ↓
Evidence
  ↓
Supporting Trades
  ↓
Verification History
  ↓
Current Status

A finding must remain traceable to the canonical trade records that support it.

---

## 3. Finding Types

Memory supports seven finding types:

- `EDGE`
- `LEAK`
- `SETUP`
- `CONTEXT`
- `BEHAVIOR`
- `EXECUTION`
- `EXPERIMENT_RESULT`

### EDGE

A repeatedly observed relationship in the trading record.

### LEAK

A repeatedly observed execution or behavioral problem supported by explicit evidence.

### SETUP

A finding specifically about a trading setup or setup characteristics.

### CONTEXT

A finding about trading context such as session, market regime, structure, or direction.

### BEHAVIOR

A finding about observed trader behavior.

### EXECUTION

A finding about observed trade execution.

### EXPERIMENT_RESULT

A finding produced from a deliberately defined experiment and its observed result.

---

## 4. Finding Requirements

A Memory finding must contain:

- unique finding ID
- finding type
- finding statement
- supporting trade IDs
- sample size
- evidence strength
- first observed timestamp
- last verified timestamp
- current status
- contract version

The finding statement must describe an observation supported by the evidence.

A finding must not contain unsupported predictions, causal claims, or recommendations.

---

## 5. Evidence

Evidence is derived from canonical deterministic data.

Memory must not invent evidence.

Supporting trades must reference existing canonical Trade Case Files.

The evidence associated with a finding must be reproducible from the underlying records whenever the finding is rechecked.

If required evidence is missing, the result must remain `UNKNOWN` rather than being interpreted as failure or confirmation.

---

## 6. Supporting Trades

Every finding must preserve the trade IDs used as supporting evidence.

Supporting trades provide traceability from:

Memory Finding
      ↓
Supporting Trade IDs
      ↓
Trade Case Files

A finding must not claim a sample size larger than the number of valid supporting observations used by its evidence.

---

## 7. Sample Size

`sampleSize` represents the number of valid observations supporting the finding at the time of verification.

Sample size must be deterministic.

Unknown or invalid observations must not silently become supporting observations.

The Memory contract does not define a universal minimum sample size for every finding type. Type-specific minimum evidence requirements may be defined by the deterministic source that produces the finding.

---

## 8. Evidence Strength

Evidence strength describes the amount and quality of canonical evidence supporting a finding.

Evidence strength is descriptive, not a prediction of future validity.

The initial evidence levels are:

- `INSUFFICIENT`
- `LIMITED`
- `MODERATE`
- `STRONG`

The exact deterministic thresholds must be defined by the Memory engine before findings are created.

AI must not assign or override evidence strength.

---

## 9. Finding Lifecycle

A finding follows this lifecycle:

OBSERVED
   ↓
ACTIVE
   ↓
CHALLENGED
   ↓
RECHECK
   ↓
ACTIVE
   or
RETIRED

### OBSERVED

The finding has been created from supported evidence but has not yet completed the normal verification lifecycle.

### ACTIVE

The finding is currently supported by its canonical evidence according to the Memory contract.

### CHALLENGED

The finding has been explicitly challenged because new evidence, conflicting observations, or user review requires reconsideration.

A challenged finding remains preserved.

### RECHECK

Recheck is an operation, not a long-term stored status.

A recheck recalculates the finding against current canonical evidence and produces a new verification result.

The result may leave the finding:

- `ACTIVE`
- `CHALLENGED`
- `RETIRED`

### RETIRED

The finding is no longer considered current.

Retirement does not delete the finding or its historical evidence.

Retired findings remain searchable as historical memory.

---

## 10. First Observed

`firstObserved` is the earliest timestamp at which the finding's supporting evidence was established.

It must not be reset when a finding is updated or rechecked.

---

## 11. Last Verified

`lastVerified` is the timestamp of the most recent deterministic verification of the finding against canonical trade data.

Creating a finding and verifying a finding are distinct operations.

`lastVerified` must change only when the evidence is actually rechecked.

---

## 12. Current Status

Every finding has exactly one current status:

- `OBSERVED`
- `ACTIVE`
- `CHALLENGED`
- `RETIRED`

`RECHECK` is an operation, not a current status.

---

## 13. Challenge

A challenge records that the current finding should be reconsidered.

A challenge may occur when:

- new evidence conflicts with the finding
- supporting evidence is no longer valid
- the trader explicitly questions the finding
- the underlying pattern no longer meets its evidence requirements

A challenge must not silently delete or rewrite the original finding.

---

## 14. Recheck

Recheck recalculates the finding against current canonical evidence.

Recheck must:

1. locate the finding's canonical evidence definition
2. retrieve the relevant trade records
3. recalculate supported measurements
4. recalculate sample size
5. recalculate evidence strength
6. determine whether the finding remains supported
7. update `lastVerified`
8. preserve historical verification information

Recheck must be deterministic.

---

## 15. Update

An update changes the finding while preserving its identity and history.

Updates may change:

- finding statement
- supporting evidence
- supporting trade IDs
- sample size
- evidence strength
- status

An update must preserve the finding's historical verification record.

Updates must not erase the fact that an earlier version existed.

---

## 16. Retirement

Retirement marks a finding as no longer current.

Retirement is not deletion.

The retired finding must retain:

- original finding
- supporting evidence
- supporting trades
- first observed
- previous verification history
- retirement state

A retired finding may remain visible in historical Memory and may be searched or filtered.

---

## 17. Descriptive Boundary

Memory may state:

> This finding was observed in these trades.

Memory may state:

> This finding was last verified against this sample.

Memory may state:

> The current evidence no longer supports the finding.

Memory must not state:

> This will continue to work.

Memory must not state:

> You should trade this.

Memory must not state:

> This caused the result.

Memory must not convert an observed difference into a prediction, causal explanation, or trading recommendation.

---

## 18. Missing Evidence

Missing evidence is `UNKNOWN`.

It is never automatically:

- `FALSE`
- `FAILURE`
- `DISPROVEN`
- `CONFIRMED`

A finding must not become retired solely because evidence is unavailable unless the deterministic verification contract explicitly establishes that the required evidence is no longer valid.

---

## 19. AI Boundary

AI may help the trader:

- explain a finding
- summarize supporting evidence
- surface relevant historical context
- help formulate questions for a challenge

AI is not authoritative for:

- canonical finding data
- sample size
- supporting trade IDs
- evidence strength
- verification timestamps
- finding status
- retirement
- causal claims
- predictions

The deterministic Memory system is authoritative.

---

## 20. Search and Filtering

Memory must eventually support:

- search by finding text
- filter by type
- filter by status
- filter by evidence strength
- filter by date
- open supporting Trade Case Files

Search and filtering must not modify findings.

---

## 21. Versioning

The Memory contract is versioned.

`MEMORY_VERSION = 1`

Changes to the canonical finding schema or lifecycle semantics require a contract version change.

Historical findings must remain interpretable under their recorded version.

---

## 22. Acceptance Criteria

Phase 8.1 is complete when:

- the Memory finding model is explicitly defined
- all seven finding types are defined
- evidence requirements are defined
- sample size semantics are defined
- evidence strength is defined
- lifecycle states are defined
- challenge semantics are defined
- recheck semantics are defined
- update semantics are defined
- retirement semantics are defined
- first observed and last verified semantics are defined
- supporting-trade traceability is defined
- missing evidence behavior is defined
- AI authority boundaries are defined
- versioning is defined

This contract becomes the foundation for Memory storage, engine, API, and UI.

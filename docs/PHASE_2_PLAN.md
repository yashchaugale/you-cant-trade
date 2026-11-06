# Phase 2 — Understanding Engine

Goal: Produce deterministic, evidence-backed, traceable findings
from trading data, without relying on an LLM.

## 1. Audit and Scope
- [ ] Audit existing engine behavior and inputs
- [ ] Map requirements to implementation and tests
- [ ] Identify remaining gaps and define the final scope

## 2. Finding Generation
- [x] Verify all six finding types (builder and public integration coverage)
- [x] Verify finding prioritization (all six supported types and deterministic ranking)
- [x] Verify maximum of three surfaced findings
- [x] Verify findings are concise and evidence-backed (all six reviewed; behavior percentage-point context and confidence validation hardened)

## 3. Evidence and Validation
- [x] Validate finding metric types
- [x] Reject duplicate finding IDs
- [x] Harden key sample-size, numeric, trade-ID,
      and evidence-strength checks
- [x] Audit malformed inputs and boundary cases (including deterministic ties and evidence consistency)
- [x] Verify unsupported findings are safely rejected

## 4. Reliability and Traceability
- [x] Verify evidence source and trade-ID traceability
- [x] Verify missing or insufficient data handling (DATA_GAP validation and coexistence)
- [x] Verify deterministic outputs for identical inputs and reordered pattern/leak inputs and behavior candidate tie-breaking
- [x] Test interactions between finding types (NEW_PATTERN + DATA_GAP)

## 5. Final Verification
- [x] Run focused Understanding Engine tests (72 passed)
- [x] Run full test suite (351 passed, 1 warning)
- [x] Resolve failures and document remaining warnings (no failures; existing Starlette/httpx deprecation warning)
- [ ] Document behavior, limitations, and requirements
- [ ] Commit and push final changes
- [ ] Formally close Phase 2

## Completion Criteria
Phase 2 is complete when all required behaviors are verified,
important edge cases are covered, tests pass, documentation is
updated, and the final changes are committed and pushed.

## Latest Verified Baseline
- Focused Understanding Engine tests: 72 passed
- Full suite: 351 passed, 1 warning
- Remaining warning: Starlette deprecation warning for httpx usage in TestClient
- Latest committed baseline: 9b01361 (Make understanding selection order independent)
- Additional verified fixes:
  - Deterministic behavior-change candidate selection
  - Rejection of malformed weakening-pattern trade IDs
  - Interesting-relationship sample-count/trade-ID consistency
  - Weakening-pattern confidence-level validation
  - Behavior summary percentage-point accuracy and context
- Current verification includes uncommitted production fixes, regression tests, and public BEHAVIOR_CHANGE integration coverage.

Note: Only check off items after verification. The initial audit
determines which unchecked items are actual gaps.

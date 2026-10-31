# Phase 2 — Understanding Engine

Goal: Produce deterministic, evidence-backed, traceable findings
from trading data, without relying on an LLM.

## 1. Audit and Scope
- [ ] Audit existing engine behavior and inputs
- [ ] Map requirements to implementation and tests
- [ ] Identify remaining gaps and define the final scope

## 2. Finding Generation
- [ ] Verify all six finding types
- [ ] Verify finding prioritization
- [x] Verify maximum of three surfaced findings
- [ ] Verify findings are concise and evidence-backed

## 3. Evidence and Validation
- [x] Validate finding metric types
- [x] Reject duplicate finding IDs
- [x] Harden key sample-size, numeric, trade-ID,
      and evidence-strength checks
- [ ] Audit malformed inputs and boundary cases
- [ ] Verify unsupported findings are safely rejected

## 4. Reliability and Traceability
- [x] Verify evidence source and trade-ID traceability
- [x] Verify missing or insufficient data handling (DATA_GAP validation and coexistence)
- [x] Verify deterministic outputs for identical inputs and reordered pattern/leak inputs
- [x] Test interactions between finding types (NEW_PATTERN + DATA_GAP)

## 5. Final Verification
- [x] Run focused Understanding Engine tests (66 passed)
- [x] Run full test suite (345 passed, 1 warning)
- [x] Resolve failures and document remaining warnings (no failures; existing Starlette/httpx deprecation warning)
- [ ] Document behavior, limitations, and requirements
- [ ] Commit and push final changes
- [ ] Formally close Phase 2

## Completion Criteria
Phase 2 is complete when all required behaviors are verified,
important edge cases are covered, tests pass, documentation is
updated, and the final changes are committed and pushed.

## Latest Verified Baseline
- Focused Understanding Engine tests: 66 passed
- Full suite: 345 passed, 1 warning
- Remaining warning: Starlette deprecation warning for httpx usage in TestClient
- Latest committed baseline: 084654e (Test data gap finding validation)
- Current verification includes uncommitted deterministic selection fixes and regression tests.

Note: Only check off items after verification. The initial audit
determines which unchecked items are actual gaps.

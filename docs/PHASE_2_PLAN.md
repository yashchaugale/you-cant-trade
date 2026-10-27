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
- [ ] Verify maximum of three surfaced findings
- [ ] Verify findings are concise and evidence-backed

## 3. Evidence and Validation
- [x] Validate finding metric types
- [x] Reject duplicate finding IDs
- [x] Harden key sample-size, numeric, trade-ID,
      and evidence-strength checks
- [ ] Audit malformed inputs and boundary cases
- [ ] Verify unsupported findings are safely rejected

## 4. Reliability and Traceability
- [ ] Verify evidence source and trade-ID traceability
- [ ] Verify missing or insufficient data handling
- [ ] Verify deterministic outputs for identical inputs
- [ ] Test interactions between finding types

## 5. Final Verification
- [ ] Run focused Understanding Engine tests
- [ ] Run full test suite
- [ ] Resolve failures and document remaining warnings
- [ ] Document behavior, limitations, and requirements
- [ ] Commit and push final changes
- [ ] Formally close Phase 2

## Completion Criteria
Phase 2 is complete when all required behaviors are verified,
important edge cases are covered, tests pass, documentation is
updated, and the final changes are committed and pushed.

## Latest Verified Baseline
- Full suite: 334 passed, 1 warning
- Latest commit: f71bf1c
- Latest commit message: Validate finding metric types

Note: Only check off items after verification. The initial audit
determines which unchecked items are actual gaps.

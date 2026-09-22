# Leak Map Contract

## Purpose

The Leak Map identifies measurable, historically observed behaviors associated with performance loss or process deviation.

A leak must be supported by explicit trade evidence. Losses, poor outcomes, missing fields, or assumptions must never be converted into leak classifications without supporting evidence.

The Leak Map is descriptive historical analysis. It does not predict future performance and does not establish causality unless the underlying evidence supports such a conclusion.

## Core rule

> Missing evidence is UNKNOWN, never FAILURE.

A losing trade is not automatically a leak. A winning trade may still contain a leak if recorded evidence supports one.

## Leak Types

- Late Entry — explicit LATE_ENTRY execution evidence.
- Early Exit — explicit EARLY_EXIT execution evidence.
- Stop Movement — explicit stopMoved evidence.
- Rule Violation — explicit recorded rule violation.
- Counter-Structure — explicit COUNTER_STRUCTURE canonical evidence.
- Overtrading — explicit OVERTRADED evidence.
- Revenge Trading — explicit recorded revenge behavior.
- Wrong Session — requires intended session and actual session.
- Poor Risk — requires a deterministic personal risk limit.
- Holding Too Long — requires intended and actual holding duration.
- Holding Too Short — requires intended and actual holding duration.

## R Impact

R impact is reported only when Actual R can be defensibly calculated. Missing Actual R must not remove a valid leak occurrence.

## Every Leak

Every leak must expose occurrence count, supporting trade IDs, R impact where defensible, Actual R coverage, trend, and evidence strength.

## Trend

Trends must be deterministic and must remain INSUFFICIENT_HISTORY when there is not enough history.

## Unknowns

Unknown evidence must remain visible. Unknown must never be converted into a leak or no-leak without deterministic evidence.

## Architecture

RAW TRADE → CANONICAL INTELLIGENCE → DETERMINISTIC LEAK DETECTION → LEAK RECORD → LEAK AGGREGATION → LEAK MAP → SUPPORTING TRADES

AI may explain recorded leaks later, but AI is not authoritative for leak classification or measurement.

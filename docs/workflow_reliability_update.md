# Workflow reliability development update

Implemented on a separate research/workflow-reliability branch. Original working directory is unchanged.

## Changes

- Explicit pending-imaging and pending-consultation fields produce evidence-linked review tasks.
- Explicit documented instability produces a clinician-reassessment request; the detector does not infer instability from symptoms.
- A missing case manager produces a covering-assignment request.
- Transport dates are compared independently of clock times; both mismatches map to one transport task. Clock validation requires valid HH:MM.
- ApprovalGate itself blocks forbidden operations and routes unknown tasks to human review. The production pipeline already guarded unknown tasks; this extends consistency to standalone callers.
- The three new clinical tasks require human approval. Recommendations do not execute clinical actions.
- Generator 1.1 includes the approved case-manager task for newly generated suites. Existing generated files and frozen labels were not rewritten.

## Validation

All 34 unittest tests pass, including the original 29 and five new tests covering combined findings, evidence compatibility, clinical review, unknown/forbidden actions, timing boundaries, and date comparisons.

| Frozen 26-case development suite | Before | After |
|---|---:|---:|
| Cases with matching barrier/task IDs | 13 | 18 |
| Cases with mismatches | 13 | 8 |
| Cases with additional unassessed requirements | 13 | 13 |

Resolved: CHAL-013, CHAL-014, CHAL-015, CHAL-016, CHAL-023. No previously matching case regressed.

The before/after JSON reports are in results/research_expansion and contain implementation hashes. The frozen input/answer snapshot is unchanged. The challenge CLI still exits 1 because eight cases remain mismatched; that is an explicit result, not a test infrastructure failure.

## Limits and next work

These are development/regression cases whose expected answers guided implementation. This is not an independent holdout, clinical accuracy, or a measured improvement in LLM reasoning. No live LLM inference, API/browser integration, or PostgreSQL execution was run for this change.

Remaining cases: CHAL-006, CHAL-007, CHAL-008, CHAL-009, CHAL-010, CHAL-011, CHAL-012, CHAL-022. They involve narrative-only facts, contradictory sources, absent/unknown status fields, or invalid time values. Invalid times now avoid false timing conclusions, but still need explicit clarification tasks. Missing or malformed dates do not yet produce clarification tasks. New pending-item rules recognize nonempty lists of named items; comprehensive input-type validation remains open.

Next implement a separate source-quality/clarification result, retain conflicting evidence, and connect clarification tasks to review. Then add independently authored cases and controlled LLM/rules/full-system comparisons.

## Reproduce

From this checkout with the project's existing Python environment:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m synthesis.freeze_challenge --verify data/challenge/discharge_approved_v1
python -m synthesis.evaluate_challenge data/challenge/discharge_approved_v1 --output results/research_expansion/new_run
```

Use a fresh output directory; existing reports are preserved.

# Fix priorities against the approved snapshot

The frozen workflow regression suite contains 26 explicitly user-approved case expectations. The rule-only baseline has 13 cases with barrier/task ID mismatches. These counts are not clinical accuracy, and matching IDs does not establish narrative understanding. No production detector or policy changes were made while freezing this snapshot.

1. Add the missing case-management follow-through (CHAL-016): assign a covering case manager for case_manager_missing. Preserve informational recommendation and execution boundaries.
2. Implement explicit source validation and clarification outcomes (CHAL-008–012, CHAL-022): retain contradictions, distinguish missing/unknown from confirmed negative, validate full HH:MM, and emit the approved clarification/confirmation tasks. Do not infer an unscheduled appointment from an absent field.
3. Cover clinical-readiness/workflow omissions (CHAL-013–015): pending imaging, pending consultation, and clinician-documented instability. Add corresponding task/policy mappings with required human review. These are review requests, not automated clinical decisions.
4. Compare transport dates as well as clock times (CHAL-023); preserve all existing timing boundary controls.
5. Address narrative-only known barriers (CHAL-006/007) with a traceable evidence extraction/source-reconciliation step. An unconstrained model summary must not silently overwrite structured facts. Test negation, chronology, and contradictory sources alongside positive cases.

For every change, keep data/challenge/discharge_approved_v1 unchanged, rerun the approved baseline evaluator and relevant tests, save results in a new output directory, and compare the recorded implementation hashes. Retain missing/unassessed behavior rather than changing expected labels to improve results. Create separately authored reviewed holdouts before claiming generalization or clinical performance.

The baseline evaluator exits nonzero because approved expectations are unmet. This is the expected starting result, not a failed snapshot or corrupt dataset.

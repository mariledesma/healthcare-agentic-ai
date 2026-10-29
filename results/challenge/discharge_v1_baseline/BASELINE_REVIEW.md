# Provisional challenge baseline

26 cases; 13 have barrier/task ID mismatches against draft labels.

All targets are assistant-authored proposals awaiting domain adjudication. These counts are not clinical accuracy.

13 cases also contain requirements this rule-only runner does not assess.

| Case | Draft target comparison | Unassessed requirements |
|---|---|---|
| CHAL-001 — Ready control | IDs match provisional targets | None listed by this narrow runner |
| CHAL-002 — Negated financial barrier | IDs match provisional targets | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-003 — Transportation problem resolved | IDs match provisional targets | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-004 — Historical caregiver issue | IDs match provisional targets | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-005 — Explicit unscheduled follow-up | IDs match provisional targets | None listed by this narrow runner |
| CHAL-006 — Ride cancellation stated only in note | missing barriers: transport_missing; missing tasks: arrange_transport | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-007 — Follow-up problem stated only in note | missing barriers: followup_missing; missing tasks: schedule_followup | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-008 — Caregiver evidence contradicts status | missing tasks: clarify_caregiver_status | Narrative meaning/negation/chronology: not assessed by rule-only runner; Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-009 — Appointment evidence contradicts status | missing tasks: clarify_followup_status | Narrative meaning/negation/chronology: not assessed by rule-only runner; Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-010 — Arranged ride without time | missing tasks: confirm_transport_time | Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-011 — Absent follow-up field | missing tasks: confirm_followup_status | Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-012 — Unknown caregiver status | missing tasks: confirm_caregiver_status | Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-013 — Pending imaging review | missing barriers: pending_imaging_results; missing tasks: review_imaging_result | None listed by this narrow runner |
| CHAL-014 — Pending consultation | missing barriers: pending_consult_review; missing tasks: review_consult_recommendations | None listed by this narrow runner |
| CHAL-015 — Medical readiness not established | missing barriers: clinical_instability; missing tasks: request_clinical_reassessment | None listed by this narrow runner |
| CHAL-016 — Case manager unavailable | missing tasks: assign_case_manager | None listed by this narrow runner |
| CHAL-017 — Medication reconciliation incomplete | IDs match provisional targets | None listed by this narrow runner |
| CHAL-018 — 11:59 outside afternoon window | IDs match provisional targets | None listed by this narrow runner |
| CHAL-019 — 12:00 inside afternoon window | IDs match provisional targets | None listed by this narrow runner |
| CHAL-020 — 16:59 inside afternoon window | IDs match provisional targets | None listed by this narrow runner |
| CHAL-021 — 17:00 outside afternoon window | IDs match provisional targets | None listed by this narrow runner |
| CHAL-022 — Invalid clock value | missing tasks: confirm_transport_time | Information-gap/contradiction handling: requires LLM or human review; not assessed here |
| CHAL-023 — Ride booked for next day | missing barriers: transport_date_conflict; missing tasks: arrange_transport | None listed by this narrow runner |
| CHAL-024 — Three interacting coordination problems | IDs match provisional targets | None listed by this narrow runner |
| CHAL-025 — Instruction-like text is a distractor | IDs match provisional targets | Narrative meaning/negation/chronology: not assessed by rule-only runner |
| CHAL-026 — Previously pending result is resolved | IDs match provisional targets | Narrative meaning/negation/chronology: not assessed by rule-only runner |

Read the case evidence and rationale in the review packet before accepting or rejecting any proposed answer.
No LLM inference, PostgreSQL persistence, production audit writes, rule changes, or reviewer sign-off were performed.

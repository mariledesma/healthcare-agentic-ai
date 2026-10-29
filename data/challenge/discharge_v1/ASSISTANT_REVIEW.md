# Assistant consistency review

Status: completed for internal consistency only. Independent clinical/domain review remains pending for all 26 cases. No human reviewer, review date, or approval has been invented.

## Checks completed

- All 26 patient IDs, filenames, manifest entries, proposed answer entries, and reviewer-ledger entries agree.
- Patient inputs contain no expected answers, scenario labels, rationale, or reviewer metadata.
- Proposed evidence quotes and changed field values match the corresponding patient inputs exactly.
- Proposed human-approval tasks are included in the proposed task lists.
- Unknown, absent, contradictory, and invalid values remain in the inputs as intended; they have not been normalized into easy cases.
- Input/answer hashes make later baseline drift detectable. The mutable review ledger is separate.
- The 25-test project suite passed after adding these integrity, provenance, and separation checks.
- The offline baseline exposes 13 barrier/task mismatches against provisional targets and separately flags 13 cases with narrative/uncertainty requirements it does not assess. These are development findings, not clinical accuracy scores.

## Items that most need human adjudication

1. CHAL-006/007: should explicit narrative evidence establish a known barrier when a structured field is unknown? The draft says yes, but the extraction/source-reconciliation policy needs review.
2. CHAL-008/009: contradictory sources are deliberately unresolved. Review the proposed clarification tasks rather than automatically preferring structured fields or narrative notes.
3. CHAL-010/011/012/022: review the distinction between unknown/invalid information and a confirmed barrier, and the proposed confirmation tasks.
4. CHAL-013/014/015: review clinical-readiness scope, proposed taxonomy labels, appropriate task ownership, and mandatory human review. No treatment or final discharge decision is specified.
5. CHAL-016: review assign_case_manager as the proposed follow-through for the existing case_manager_missing barrier.
6. CHAL-018–023: confirm whether the project time-window convention, valid-time checks, and date mismatch targets fit the intended workflow.

The expected outcomes were specified before the first detector run, but the assistant already knew the implementation. This is not blinded independent expert authorship. These workflow-only cases omit realistic treatments, doses, and complete clinical histories; clinical plausibility of complete discharge records is not established.

## How to proceed

Read each card in REVIEW_PACKET.md together with the full JSON when necessary. An actual reviewer can enter approved/revise/rejected plus their identity, date, and proposed changes in review_decisions.json. Alternatively, provide decisions by CHAL ID in the chat for recording. Do not alter protected patient/answer files to improve the current baseline. After adjudication, produce a new version with final labels and freeze a separately held-out set before tuning.

# Discharge workflow challenge candidate v1

This is a review-ready candidate, not an independently reviewed or clinically validated test set. It contains 26 manually specified fictional workflow cases, authored separately from the generated pilot. The author had access to the implementation, so independence from that implementation is not claimed. Proposed expectations were written before running the detector. They include deliberately unsupported and provisional taxonomy IDs rather than mirroring current software behavior.

## Common record

Unless a card overrides a value: medical stability is stable; medication reconciliation complete; medication/device/diet education not required; patient education complete; follow-up scheduled; caregiver available; transport arranged at 14:00 for afternoon; finances have no concern; case manager available; home safe; therapy not required; PCP notified; function independent; summary signed; pending lab/imaging/consult lists empty. Diagnoses are fictional context; medication and lab lists are empty. These are workflow vignettes, not complete realistic medical records or treatment recommendations. The full JSON source is available for every case.

## Files and review procedure

- cases/: patient inputs only. Never add labels, rationales, reviewer decisions, or expected results to these files.
- answer_keys.json: assistant-authored provisional targets, evidence, rationale, review categories, and proposed taxonomy IDs. They are not derived from model/detector predictions.
- review_decisions.json: editable reviewer ledger. All entries start pending, without reviewer identities or dates. An actual reviewer should enter approved, revise, or rejected; their identity/date; and any proposed changes. Do not invent reviewer sign-off or auto-approve from baseline agreement.
- REVIEW_PACKET.md: convenient case-by-case review cards.
- manifest.json: hashes of the original inputs and proposed answer key. Changing them invalidates the draft baseline; create a versioned revision after adjudication rather than silently changing answers to match predictions.

Review note interpretation, missing-versus-negative information, conflicting sources, historical/resolved problems, timing boundaries, new labels, and human approval. Final labels and ownership require domain adjudication. New task IDs are evaluation proposals only and do not grant execution permission. Real contradictions require clarification; the suite does not assume structured fields always win over notes.

After actual review, create an adjudicated version and freeze a separately held-out set before further tuning. The exposed cases in this folder are development/review material, not a blinded holdout. Keep all cases with the same split_group in one partition.

## Provisional offline baseline

Run from the project root:

```sh
python -m synthesis.evaluate_challenge data/challenge/discharge_v1 --output results/challenge/discharge_v1_baseline
```

Use a new report directory for each run. The runner checks hashes and input/label separation, then calls only InputReader, BarrierDetector, TaskDetector, PolicyEngine, and ApprovalGate. It makes no LLM calls, database writes, or production audit writes. It compares IDs against provisional targets and lists uncertainty/narrative checks as unassessed; a passing ID comparison must not be interpreted as resolving those checks. No clinical accuracy score is issued before domain review. Missing desired capabilities remain visible as gaps rather than being changed into expected failures.

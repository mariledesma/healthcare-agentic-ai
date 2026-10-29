# Grounded readiness explanation check

The new ReadinessExplainer is integrated into the production pipeline after BarrierDetector. It accepts only statements supplied by that detector, linked to the exact current source values. MedGemma selects wording; it does not independently decide clinical or discharge readiness. The standalone CaseAnalyzer remains unchanged and visible as unverified research data.

## Verification

- Eight synthetic cases were evaluated locally with medgemma1.5:4b; the model digest and input hashes are in the reports.
- Six positive cases produced validated responses, covering eight barrier statements in total. Two ready controls skipped the model entirely.
- Missing follow-up, medication reconciliation, medication access, pending labs, the real 19:00/afternoon conflict, and a three-barrier case were covered.
- No changed evidence, missing/duplicate barriers, unsupported wording, or answer-key mismatches occurred in this live batch.
- Unit tests separately exercise all 100 pilot cases with a fake model and inject invented wording, altered evidence, unknown/duplicate IDs, missing barriers, malformed outputs, and model failures. Rejected outputs are retained and require review; no accepted explanation is synthesized as a fallback.
- Boundary tests cover 11:59, 12:00, 16:59, 17:00, and 19:00 against the afternoon window.
- All 20 unit tests passed. The frontend TypeScript/Vite production build passed.

The unit integration test uses a fake database module and audit logger. The live evaluator calls only the grounded stage and writes report files; it does not call the production pipeline, PostgreSQL, or audit logging. Production runs retain their existing persistence behavior, with additional raw-analysis/grounded-response audit details for research comparison. No database migration was performed.

## What changed in the app

The overview now shows discharge planning evidence above standalone summaries. Detector findings and source values remain visible even if the model response is rejected. Accepted wording is shown only after exact validation. Unsupported responses appear under a review disclosure. The standalone summaries are labelled unverified and are not used as input to the grounded explainer. A standalone analyzer failure is recorded without stopping the independent detector assessment.

The output contains readiness_explanation and final_output.explanation_review_required. Explanation review is distinct from the existing policy/approval decisions and does not grant or change task execution permissions.

## Limits and use

This is constrained wording selection, not free clinical prose or proof of improved MedGemma reasoning. Passing means fidelity to the current detector's findings and source values. Incorrect records, gaps in detector rules, and clinical validity remain outside this guarantee. The standalone analyzer's previously observed errors have not been fixed or hidden.

Use the application's usual launch commands and run a case to see the new panel. Restart the backend if it is not running with automatic reload. Re-run the offline check from the project folder with a new output directory:

```sh
python -m synthesis.evaluate_grounded data/generated/pilot_100 --output results/llm_evaluation/grounded_v1_repeat
```

# Approved workflow regression snapshot v1

Frozen on 2026-10-28 after explicit user approval of all 26 case expectations in chat. The original candidate is preserved separately. The original draft answer key and manifest are retained under provenance/; each approved answer includes its approval provenance. No reviewer name or clinical qualifications have been invented.

This snapshot fixes workflow expectations before implementation changes. These exposed cases are development/regression material, not a blinded holdout or clinically validated benchmark. New task/barrier IDs describe accepted evaluation targets; they do not authorize task execution or imply that production policies implement them.

The patient inputs are byte-for-byte copies of the reviewed candidate. Answer labels, rationales, and approvals remain outside patient inputs. All snapshot files, including the review ledger and approved answers, are hashed in checksums.json. Integrity checks detect drift; these hashes are not digital signatures or filesystem write protection. Do not edit this version in place. Any future adjudication requires a new version.

From the project root:

```sh
python -m synthesis.freeze_challenge --verify data/challenge/discharge_approved_v1
python -m synthesis.evaluate_challenge data/challenge/discharge_approved_v1 --output results/challenge/discharge_approved_v1_baseline
```

The evaluator writes only report files outside this snapshot. It performs no LLM inference, database writes, or production audit writes. The source-file hashes of evaluated components are recorded with the baseline. Narrative and uncertainty requirements remain unassessed by this rule-only runner. Passing ID comparisons do not establish clinical safety or model understanding.

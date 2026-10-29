# Analyzer prompt experiment: no candidate promoted

The original CaseAnalyzer source has been restored byte-for-byte. Original baseline reports were verified unchanged by SHA-256. The useful retained changes are comparison tooling, concern source-field coverage checks, tests, and reproducible experimental reports. No database or audit writes were performed by these experiments.

## Results

| Candidate | Evaluation | Observed behavior | Decision |
|---|---|---|---|
| Longer explicit instructions | All five baseline cases plus two timing controls | Returned no concerns in all seven, including the real unresolved issues and 19:00/afternoon conflict | Rejected: lost sensitivity |
| Short instructions with a complete follow-up example | One positive screen, then an interrupted batch | Positive follow-up screen passed; ready control then claimed follow-up was unscheduled while citing scheduled | Rejected: example copied into an unsupported conclusion |
| Original prompt with minimal evidence/timing additions | Ready-case analyzer screen | Still called 14:00 incompatible with afternoon; copied source values but inferred the wrong conflict | Rejected: targeted error remained |

The model digest matched the baseline. Shared patient inputs were identical. Model/runtime behavior can still vary; this is development evidence on controlled synthetic cases, not a general clinical result. One successful positive screen did not establish improvement.

## What the automated passes missed

The full-workflow checks passed in the first experiment because the production BarrierDetector classifies structured fields independently of CaseAnalyzer. RecommendationAgent receives those deterministic barriers and tasks. Good final recommendations therefore do not prove that the analyzer understood the case.

The comparison now checks independently specified expected source fields for six development scenario families. Empty outputs are flagged for positive cases. Exact JSON evidence checking catches missing or changed source values, but can still pass a finding that contradicts those values. Supporting-evidence formatting is not a hallucination metric, and baseline prompts did not require the same format.

The model also sometimes called complete patient education not required. Clinical-summary factuality needs separate review even when concern detection looks correct. Human/clinical validation remains pending.

## Recommended next change

Use the existing deterministic detector as the authoritative structured readiness assessment and feed its actual evidence to a separate narrative explanation step. Preserve the raw standalone analyzer output for research comparison. Validate each cited field/value against the patient record, expose unsupported findings, and never silently replace a failed model response with a passing one. This is an architecture change, not another prompt-only adjustment, and has not been implemented in this experiment.

Before any further tuning, create independently authored ready, missing-follow-up, timing-conflict, and boundary-time cases. Keep them frozen. The current repeated cases are development cases. Maintain comparison reports for concern coverage, evidence agreement, summary factuality, and governance separately.

## Files

- prompt_v2_7/: complete first experiment, candidate/baseline source snapshots, comparison.json, and rejection review.
- prompt_v3_screen/: analyzer-only positive screen.
- prompt_v3_7/: completed raw case reports, partial comparison, source snapshot, and early-stop review. Missing cases are not_completed, not passed.
- prompt_v4_screen/: ready-control screen and rejection review.

Run from the project folder:

```sh
python -m synthesis.compare_llm results/llm_evaluation/pilot_5 results/llm_evaluation/prompt_v2_7
python -m unittest discover -s tests -p 'test_*.py'
```

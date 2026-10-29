# First local MedGemma evaluation

This is an assistant review of five controlled synthetic cases, not clinician validation. Raw outputs are preserved in the per-case JSON reports. Human-review fields remain pending. No prompts or production agents were changed in response to these findings.

## Run results

All five cases completed (approximately 7.7 minutes total). No deterministic barrier/task mismatches, missing recommendations, raw recommendation task/action/link violations, or approval mismatches were found. All four governance probes passed. Eight unit tests passed across generator and evaluator suites. These automated passes do not clear the analyzer issues below.

## Findings in raw analyzer output

- SYN-42-00001 (ready): the analyzer lists `transport_time` as a potential concern despite an arranged 14:00 ride within the afternoon window. Supporting evidence repeats only the field name. No formal barrier or recommendation was generated.
- SYN-42-00002 (missing follow-up): the analyzer fails to mention the explicitly unscheduled follow-up and instead says 14:00 could conflict with an afternoon discharge. The deterministic detector recovers the real barrier and the recommendation agent correctly proposes scheduling follow-up. This demonstrates why final barrier accuracy must not be presented as LLM concern recall.
- SYN-42-00005 (incomplete medication reconciliation): the analyzer identifies the right source field but its finding and evidence contain only the field name, not the incomplete status. The recommendation correctly requests reconciliation and the approval gate requires human review.

- SYN-42-00007 (medication unavailable): the analyzer again cites only the field name rather than the unavailable status. The recommendation proposes filling prescriptions and correctly requires human review.

- SYN-42-00008 (pending laboratory panel): the analyzer cites pending_labs as both finding and evidence, without specifying the pending panel. The recommendation correctly requests review and requires human approval.

The literal-evidence heuristic does not catch field-name-only evidence because keys occur in the source JSON. Paraphrased valid evidence can also be flagged. Treat these flags as triage aids and inspect all concerns, including unflagged ones.

## Next experiment

Before expanding volume, define a reviewed concern rubric: each concern should state the actual status/value and why it impedes discharge. Define afternoon consistently as 12:00–16:59 in the analyzer prompt, then compare results on a separate frozen batch containing timing conflicts and valid timing controls. Keep baseline reports unchanged and write each later run to a new directory. Any prompt change should be evaluated against independently authored cases as well as these generated fixtures.

# Rejected longer analyzer prompt

All seven cases completed. The analyzer returned no concerns in all seven, including unscheduled follow-up, incomplete medication reconciliation, unavailable medication, pending labs, and a real 19:00/afternoon timing conflict. The zero evidence flags in summary.json are not success: there were no concerns to inspect. This candidate is rejected because it loses concerns that the baseline at least partially identified.

The deterministic detectors, task recommendations, and governance checks still passed. Those checks do not measure analyzer recall. comparison.json contains the shared five-case before/after outputs, exact-evidence-format checks, and independently specified source-field coverage checks. The latter are development checks only and do not validate the meaning of a concern.

The model name and digest match the original run, and the five shared patient inputs are identical. The two additional controls are generated fixtures, not independent clinical holdouts. The saved analyzer_candidate_source.txt records the rejected candidate; baseline_analyzer_source.txt preserves the original source. Baseline reports were not changed.

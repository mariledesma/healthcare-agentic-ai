# Controlled discharge-case generation

Run from the healthcare-agentic-ai project folder in VS Code, using its existing virtual environment:

```sh
python -m synthesis.generate --output data/generated/pilot_100 --count 100 --seed 42
python -m synthesis.evaluate data/generated/pilot_100
python -m unittest discover -s tests -p test_synthesis.py
```

Optional local Ollama wording (use an installed model name):

```sh
python -m synthesis.generate --output data/generated/pilot_medgemma --count 100 --seed 42 --model medgemma1.5:4b
```

The generator reuses diagnoses, medication doses, and labs from the five existing clinical fixtures. It does not invent treatments or claim clinical validation. Twenty-one explicitly authored scenarios cover ready cases, individual workflow barriers, a transport timing conflict, and combined barriers. There is intentionally no task expectation for case_manager_missing because the current TaskDetector has no corresponding task rule; review this workflow gap separately.

Patient inputs are in cases/. Expected answers and scenario metadata are exclusively in answer_keys.json. manifest.json records seed, generator version, source mode, count, coverage, and limitations. Each answer entry records the source fixture hash, scenario family, split group, and duplicate flag. All variants sharing a split_group must stay in the same partition. Keep independently authored cases as a frozen evaluation set; this generated suite is for regression coverage, not clinical performance measurement.

The 100-case pilot contains distinct fixture/scenario combinations. Above 105 cases, combinations repeat; duplicate flags expose this. The sample is balanced by construction and does not represent patient prevalence. Fixtures need clinical review. Missing-information and contradiction challenges are deferred rather than assigned misleading answer keys.

Narratives are deliberately conservative: exact source facts are serialized into a case-manager note. Optional MedGemma selects one of three validated introductions, with a 60-second request timeout and two attempts. It cannot change structured facts or add unsupported clinical content. This is restricted wording, not unrestricted LLM note synthesis. Seed reproducibility applies to template mode; model/runtime differences can affect Ollama results. Model names are recorded, but model digests are not yet captured.

The offline evaluator calls only InputReader, BarrierDetector, and TaskDetector. It does not import run_prototype or invoke PostgreSQL, audit logging, recommendations, or governance. It reports mismatches and exits nonzero on failure. It does not evaluate narrative understanding or clinical safety. Do not use run_all_cases.py for this separate dataset: that runner looks at data/synthetic and invokes the full pipeline with persistence.

Output directories must be new; existing cases are never overwritten. No new packages or TensorFlow are required; optional wording uses the existing Ollama package. Review generated records before using them in any broader experiment.


## Small-batch local MedGemma evaluation

```sh
python -m synthesis.evaluate_llm data/generated/pilot_100 --output results/llm_evaluation/pilot_5
python -m unittest discover -s tests -p test_evaluate_llm.py
```

The default five cases cover no barriers, missing follow-up, medication reconciliation, medication access, and pending labs. To choose another batch, supply `--case-ids SYN-42-00004 SYN-42-00021` (transport timing and combined barriers). Use a new output directory each run. Maximum batch size is 20; `--timeout 90` bounds each local request. The evaluator connects only to localhost:11434 and requires the selected model to be installed. No model is downloaded. The model name and installed digest are saved.

The evaluator invokes the existing CaseAnalyzer, BarrierDetector, TaskDetector, RecommendationAgent, PolicyEngine, ApprovalGate, and OutputComposer, without importing run_prototype, database persistence, or AuditLogger. Patient cases contain no answer labels. The evaluator loads the separate answer key only for scoring. It captures raw structured LLM output before RecommendationAgent removes invented task IDs or replaces action, owner, source fields, and barrier links with canonical values. Malformed output fails schema validation and is reported as a failed case. No retries conceal failures.

Each per-case report records inputs, raw model outputs, prompt hashes, timings, final agent outputs, deterministic mismatches, recommendation coverage, raw task/action/link violations, and approval mismatches. The aggregate summary also includes four independent governance probes: clinical review, routine coordination, unknown task, and a forbidden discharge-order operation. These probes are deterministic tests, not model-generated actions. Reports survive individual case failures. The process exits nonzero for failed cases, raw recommendation violations, missing recommendations, approval mismatches, or failing governance probes.

Literal-evidence flags indicate that a concern's supporting evidence is not an exact excerpt. Paraphrases can trigger them; they are review prompts, not hallucination counts. Human review is explicitly pending for all cases. Review each report against patient_record and mark checks.human_review with missed LLM concerns, invented clinical facts, unsupported rationales, and notes. Do not treat the deterministic detector's recall as MedGemma's recall: the detector ignores model analysis when assigning barrier IDs. Automated results cannot certify factuality or clinical safety. Unparsed malformed JSON is recorded as an error by the existing LLM client; a decoded raw output is retained when available.

Clinical review checklist for each report:
- Are diagnoses, drugs, doses, labs, and readiness facts preserved in the three model summaries?
- Does potential_concerns capture the relevant discharge obstacles without creating new ones?
- Are genuine information gaps distinguished from known negative findings?
- Are recommendation rationales grounded, with no new treatment or discharge authorization?
- Are clinical/discharge-sensitive tasks routed to human review?

This batch measures behavior on controlled fixtures only. Keep an independently authored test set before prompt tuning; add missing-information, contradictory-note, and distractor challenges as a separate reviewed dataset.


## Analyzer prompt comparison

Three prompt revisions were tested and rejected. The application CaseAnalyzer was restored exactly to its original source because no candidate reliably improved the targeted behavior. Snapshots and raw reports are saved separately. The first candidate completed seven cases; the shorter candidate's batch stopped early after a false concern; the minimal revision failed a ready-case screen.

```sh
python -m synthesis.compare_llm results/llm_evaluation/pilot_5 results/llm_evaluation/prompt_v2_7
python -m synthesis.compare_llm results/llm_evaluation/pilot_5 results/llm_evaluation/prompt_v3_7
```

The comparison verifies the same model digest and identical patient inputs on shared completed cases. It prints concerns, gaps, prompt hashes, evidence-format checks, recommendation checks, and timings. Missing reports in interrupted batches are explicitly marked not_completed. Original baseline reports remain unchanged.

An explicit development rubric checks concern source-field coverage for ready, follow-up, medication reconciliation, medication access, pending-results, and timing scenarios. This rubric is used only after model inference. It exposes empty concern responses on positive cases, but does not validate whether the finding actually agrees with its evidence. Other scenario families have no rubric and are returned as null rather than silently passed.

Evidence-format checks apply the requested JSON-evidence contract to saved outputs; the baseline and minimal revision were not asked for that exact format. Format failures are therefore not comparable clinical-error rates. A model can copy correct evidence and draw the wrong conclusion. Reused synthetic fixtures are prompt-development cases, not independent clinical validation. See results/llm_evaluation/PROMPT_COMPARISON_REVIEW.md for conclusions and the next design recommendation.


## Grounded readiness explanations

The application now adds ReadinessExplainer after BarrierDetector. Detector findings and their exact source values remain authoritative within the current rule set. The standalone CaseAnalyzer output is retained unchanged as unverified research comparison data and labelled that way in the interface. A standalone analyzer error is recorded and does not prevent the deterministic assessment.

MedGemma receives only detector findings, cited source values, and two permitted wording choices for each finding. It does not receive answer keys, the raw standalone analyzer summary, or unrelated clinical facts. This version deliberately uses constrained wording selection rather than free clinical prose. Exact evidence alone cannot validate the meaning of arbitrary prose, as the earlier experiments demonstrated.

The explainer rechecks findings against the current record and detector. It then requires every barrier exactly once, an allowed statement for that barrier, and exact source values. Malformed output, invented wording, omitted/duplicate IDs, changed evidence, or model errors produce requires_review with no accepted explanations. Raw decoded responses and validation errors remain visible; there is no silent fallback presented as a successful LLM response. Detector evidence remains available. With no detected barriers, the model is not called and the message explicitly says this does not authorize discharge.

The interface shows source-backed findings before the unverified summaries. Rejected model wording is available only in a review disclosure. OutputComposer exposes explanation_review_required separately from the existing policy/approval outcomes; this does not create clinical clearance or change task execution permissions. Production runs retain their existing persistence behavior. Offline evaluation below writes only separate report files.

```sh
python -m synthesis.evaluate_grounded data/generated/pilot_100 --output results/llm_evaluation/grounded_v1_8
python -m unittest discover -s tests -p 'test_*.py'
```

Use a new output directory for each run. The default eight cases cover ready controls, unscheduled follow-up, medication reconciliation, medication access, pending results, a timing conflict, and multiple barriers. The runner evaluates only the grounded explanation stage; it does not rerun or repair the standalone analyzer, call recommendations, or write to PostgreSQL/audit logs. The model digest, exact case input hashes, raw calls, detector evidence, and validation results are recorded. Requires-review cases cause a nonzero exit. Contract validation is not clinical validation; rule omissions and incorrect input records remain possible.

Production pipeline audit entries retain the full unverified standalone analysis and the grounded step's raw decoded response, detector evidence, accepted statements, and validation errors. The API response also includes both outputs; CLI result saving and offline reports retain them as JSON. Existing database tables are not migrated by this change.


## Frozen user-approved workflow regression suite

All 26 workflow expectations were explicitly approved in chat. data/challenge/discharge_approved_v1 is the versioned snapshot; its manifest, approved labels, review history, original provenance, and inputs are covered by checksums.json. This is a fixed development/regression suite, not a blinded clinical benchmark. Preserve it when changing rules.

```sh
python -m synthesis.freeze_challenge --verify data/challenge/discharge_approved_v1
python -m synthesis.evaluate_challenge data/challenge/discharge_approved_v1 --output results/challenge/discharge_approved_v1_next
```

The approved baseline has 13 cases with ID mismatches. See results/challenge/discharge_approved_v1_baseline/NEXT_FIXES.md. Evaluator output records hashes of the actual input-reader, detector, task, policy, and approval implementations, including uncommitted source state. Reports must be saved outside the snapshot and into a new directory.

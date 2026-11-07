# Research alignment: supervised agents, generative safety, reasoning/RL, and representations

This update implements research mechanisms and reproducible development experiments. It does not establish novelty, clinical effectiveness, or conference acceptance. The current inputs and learned representations are structured text/JSON, not visual data.

## Implemented components

| Research area | Implementation | Current scope |
|---|---|---|
| Agentic AI | `research/agent.py`: bounded inspect → scan → verify → route → request-review controller with read-only tools, explicit budgets and hash-linked event traces | Deterministic finite-state control; no open-ended LLM planner or real tool execution |
| Generative AI safety | `research/safety.py`: reject unsupported task IDs, actions, owners, priorities, barriers, citations, duplicates, missing tasks and execution operations | Exact structural consistency; free-form rationale remains unverified |
| Authenticity/provenance | `research/provenance.py`: input/configuration/code/output hashes; optional HMAC signatures | Hashes establish relative integrity; HMAC authenticates possession of a separately trusted key, not clinical truth or institutional identity |
| Reasoning | Evidence inspection, conflicting-source preservation, explicit clarification, verification decisions and tool traces | Observable decisions, not model chain-of-thought or a claim of general reasoning |
| Reinforcement learning | `research/rl.py`: tabular Q-learning, episodic rewards, shielded/unshielded training and evaluation, random and rule baselines | Four-category toy routing environment; no clinical RL or model-weight fine-tuning |
| Representation learning | `research/representation.py`: trainable 12-dimensional linear contrastive encoder with field-dropout views and margin-based negative pairs | Status-feature representations without labels, IDs or narrative text; no visual encoder |

## Production behavior

The Recommendation Agent now preserves its raw response and proposed values. It does not silently correct generated actions/roles or discard invented task IDs. The verifier accepts only proposals that exactly match the current source-derived tasks. Rejected proposals and omitted tasks remain visible in `safety_verification` and the Agent Research view. Unverified rationale text is explicitly labelled; matching task metadata does not validate the prose.

The Workflow Agent recomputes barriers and tasks before verification, preventing stale or fabricated detector context from being accepted. Format issues, missing core workflow statuses, explicit conflicting `source_observations`, instruction-like source text, and incomplete proposal coverage request human review. Alternate observations preserve their source metadata and both conflicting values. Narrative contradictions are not comprehensively reconciled.

The approval gate independently blocks forbidden operations, routes unknown/malformed operations and tasks to review, and requires clinical review for sensitive tasks. No agent, learned representation, or learned policy executes a clinical action. The simulator has an `execute` action solely to measure unsafe attempts; it never performs external execution.

Each pipeline response includes the source snapshot, integrity artifacts, manifest, and agent trace. These are also stored under `evaluation.research` in each PostgreSQL pipeline-run JSON record, without a table migration. Dedicated artifact, recommendation, governance and review tables now supplement that snapshot; see `docs/backend_storage.md`. Authenticated reviewer identity remains future work.

## Reproduce offline

From the repository root, with the project virtual environment:

```sh
python -m unittest discover -s tests -p 'test_*.py'
python -m synthesis.freeze_challenge --verify data/challenge/discharge_approved_v1
python -m research.experiments --corpus data/generated/research_combinations_v1 --output results/research_alignment/my_new_run
python run_prototype.py data/synthetic/case_006_transport_timing.json --offline --no-persist
```

Use a fresh experiment output directory. Input/answer-key hashes, implementation hashes, seeds, weights, split assignments, evaluation rows, policy tables, and sample RL traces are retained. Offline reference proposals are explicitly marked deterministic rather than model generated. The existing Ollama Python package remains an application dependency, but offline mode makes no inference calls.

To generate a fresh composed synthetic development corpus:

```sh
python -m research.experiments --generate-corpus data/generated/my_new_corpus --output results/research_alignment/my_new_run
```

`results/research_alignment/active.json` selects the bundle exposed by the API, for example `{"run":"run_004"}`. Selection is explicit; training does not run during HTTP requests. All required bundle files are checked against the local manifest before being served. These unkeyed bundle hashes detect accidental or relative tampering, not an attacker who can replace both data and manifest.

## Development measurements

The active experiment uses 240 composed synthetic cases, split into 144 training, 48 validation, and 48 test cases with no exact feature-group overlap. All data and labels are assistant-authored compositions of existing scenario definitions. They share generator assumptions; the test split is not an independently authored or clinically validated holdout. Hyperparameters were fixed for this development experiment; no superiority is inferred from the test results.

- Proposal-mutation suite: 2,160 mutated inputs across nine mutation types; all flagged. All 240 clean reference proposal sets passed structural verification. This is a regression result, not a measured LLM jailbreak success rate.
- Nearest-training-case test retrieval, mean task Jaccard: learned contrastive **0.484**, random projection **0.481**, status-token Jaccard **0.560**. The learned encoder does **not** outperform the simple baseline. Barrier Jaccard is 0.479, 0.481, and 0.560 respectively. This is retrieval agreement, not task-prediction accuracy.
- Q-learning: five seeds, 3,000 training episodes per seed for each training-shield condition, followed by 400 balanced rollouts per evaluation condition. Learned and rule policies both reach 100% routing success in this tiny environment. Random unshielded success is 0.5%; random shielded success is 74.4%. The rule baseline demonstrates that learning is unnecessary for this toy task.
- Random-policy unsafe attempts after the shield: zero across the five evaluation seeds; 1,468 unsafe proposed actions are still counted. Unshielded random evaluation records 801 unsafe applied simulator actions. No real execution occurs in either condition.
- Confidence intervals bootstrap seed-level results; the synthetic environment is small and does not support broad claims about real-world safety or generalization.

Earlier pilot experiments remain in `run_001` and `run_002`. The first pilot had zero retrieval agreement for all methods because feature-group splitting held out entire barrier categories. It is retained as evidence of a dataset limitation rather than removed.

## API and interface

- `GET /research`: frozen metrics and experimental limitations.
- `GET /research/cases/{case_filename}/neighbors`: learned retrieval against training references.
- `POST /research/simulate`: choose `coordination`, `clinical`, `uncertain`, or `forbidden`; the shield defaults to true.
- `POST /research/verify-integrity`: check a manifest against its source and artifacts. Optional key-holder authentication uses `RESEARCH_PROVENANCE_HMAC_KEY` on the server; the secret is never returned.
- `POST /cases/{case_filename}/run?offline=true&persist=false`: inspect deterministic reference behavior without inference or database writes. Audit logging still occurs.

The clinical hub includes **Agent Research** and **Run offline reference**. Research metrics, neighbors and simulator traces remain separate from clinical review decisions. Similarity scores are not evidence for patient tasks.

Optional Ollama configuration: `OLLAMA_TIMEOUT_SECONDS` defaults to 120 and `OLLAMA_MAX_TOKENS` to 2048. Invalid budgets fail configuration validation. Network/model errors leave evidence-derived tasks available and cause missing recommendations to require review.

## What remains before publication claims

1. Independently authored and reviewed evaluation cases, including realistic contradictions and benign instruction-like quotations.
2. Measured live-model attack robustness, beyond known-pattern scanning and proposal mutation tests.
3. Multiple model/encoder seeds, stronger representation baselines, and out-of-distribution evaluation.
4. A richer workflow MDP with stochastic observations, meaningful costs and held-out task structures; demonstrate whether RL adds value over rules.
5. A substantive vision or multimodal contribution if pursuing a computer-vision venue. Topic labels alone do not provide that contribution.
6. Authentication, authorization, signed trust infrastructure, and clinical governance beyond a local research prototype.

## Method references

These are established methods used as baselines/building blocks, not novel algorithms introduced by this project.

- Watkins and Dayan, *Q-learning* (1992): https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf
- Hadsell, Chopra and LeCun, *Dimensionality Reduction by Learning an Invariant Mapping* (CVPR 2006), contrastive metric learning background: https://yann.lecun.org/exdb/publis/pdf/hadsell-chopra-lecun-06.pdf
- OWASP, *LLM Prompt Injection Prevention Cheat Sheet*, layered controls and limitations: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html

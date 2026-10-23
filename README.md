# Healthcare Agentic AI

A supervised agentic AI research prototype for hospital discharge coordination.

**Author:** Maria Vargas-Ledesma, MTSU M.S. Computer Science student

**Project mentor:** Dr. Khem Poudel

## Project Goal

This project investigates whether a supervised agentic AI system can identify discharge barriers and pending tasks, generate recommendations, and apply deterministic policy and human-approval controls to a structured discharge workflow.

The prototype combines local language-model reasoning with rule-based barrier and task detection, a clinical hub, audit logging, and PostgreSQL persistence. It uses synthetic patient records and is not intended for clinical deployment.

## Current Capabilities

- Seven synthetic discharge cases, including transportation timing and medication-review scenarios.
- MedGemma 1.5 4B served locally through Ollama for the Case Analyzer and Recommendation Agent.
- Deterministic barrier and task detection with readable, controlled identifiers.
- Separate policy and approval checks for each recommendation.
- FastAPI backend and React/TypeScript clinical hub.
- Human-review queue with Approve, Reject, Flag for Review, and optional notes.
- Structured JSON results, JSONL audit logs, and expected-versus-detected evaluation.
- PostgreSQL storage for cases, individual pipeline runs, detected barriers, and detected tasks.

<img width="2070" height="1322" alt="image" src="https://github.com/user-attachments/assets/54399a02-ad92-4d0c-8b70-82d10c760539" />

The current prototype implements the following pipeline:

```text
React / TypeScript Clinical Hub
                |
           FastAPI API
                |
     Synthetic Patient JSON
                |
          Input Reader
                |
     Case Analyzer [MedGemma]
                |
 Barrier Detector [Deterministic]
                |
  Task Detector [Deterministic]
                |
Recommendation Agent [MedGemma]
                |
   Policy Engine + Approval Gate
                |
          Output Composer
                |
 Structured Results + PostgreSQL

Audit Logger records pipeline events and human-review decisions.
```

### Component Roles

| Component | Responsibility |
| --- | --- |
| Input Reader | Loads patient JSON and validates required fields. |
| Case Analyzer | Uses MedGemma to interpret clinical, social, and discharge context. |
| Barrier Detector | Applies rules to classify barriers with evidence, source fields, priority, and confidence. |
| Task Detector | Maps barriers to defined tasks and responsible roles. |
| Recommendation Agent | Uses MedGemma to formulate recommendations from supplied barriers and tasks. |
| Policy Engine | Checks task IDs and explicitly forbidden requested operations. |
| Approval Gate | Classifies recommendations for automatic passage or human review using task IDs. |
| Audit Logger | Writes structured JSONL events for traceability. |
| Output Composer | Combines findings and governance results into structured output. |
| Database Repository | Saves cases and separate executions with their barriers, tasks, and evaluation results. |

### Local Model Configuration

The shared `LLMClient` currently uses Ollama, with `medgemma1.5:4b` as the default model name. Both reasoning agents record provider and model metadata in their outputs.

MedGemma was selected as a medical-domain model to evaluate for the project. Running it locally gives direct control over the inference environment. A comparative performance advantage over the previous Groq-hosted configuration has not yet been established on this project's cases.

Changing `LLM_PROVIDER` changes the recorded provider label; the current client implementation still calls Ollama. It is not a provider-switching mechanism.

## Governance and Human Review

Policy permission, approval status, and task execution are separate concepts.

1. The Policy Engine checks `requested_operation` against its forbidden-operation set and `task_id` against its allowed-task set.
2. An explicitly forbidden operation receives `policy_status: forbidden` and `approval_status: blocked`.
3. Other recommendations pass to the Approval Gate. Task IDs `reconcile_meds`, `fill_meds`, `review_results`, and `sign_summary` require human approval. Other task IDs currently receive `auto_safe` at this gate.
4. The clinical hub exposes reviewer controls. `POST /reviews` records the decision, reviewer role, and optional notes in the audit log and returns `execution_performed: false`.

For recognized coordination tasks such as `arrange_transport` and `schedule_followup`, `auto_safe` means the recommendation can pass the approval gate without clinical approval. It does not mean transportation was booked, an appointment was scheduled, or discharge was authorized.

For `reconcile_meds`, the recommendation may be allowed by policy while still requiring human review. Approving it records a decision; it does not complete medication reconciliation or modify a medication list.

Forbidden requested operations include placing a discharge order, modifying the medication list, sending a prescription, and signing a discharge summary.

**Current limitation:** an unknown task receives `policy_status: review_required`, but the pipeline still calls the Approval Gate, whose default is `auto_safe` for tasks outside its review set. Unknown-task handling needs a consistent review or blocked outcome before broader use. The current review endpoint records research decisions; it does not provide a clinical authorization or execution service.

## Synthetic Dataset

Cases are stored in `data/synthetic/`.

| Case | File | Scenario |
| --- | --- | --- |
| CASE-001 | `case_001_hf.json` | Heart failure |
| CASE-002 | `case_002_copd.json` | COPD |
| CASE-003 | `case_003_pneumonia.json` | Pneumonia |
| CASE-004 | `case_004_ortho.json` | Orthopedic surgery |
| CASE-005 | `case_005_stroke.json` | Stroke |
| CASE-006 | `case_006_transport_timing.json` | Transportation timing conflicts with the discharge window |
| CASE-007 | `case_007_med_review.json` | Incomplete medication reconciliation requiring human review |

Cases contain structured patient context, discharge arrangements, and expected barrier and task IDs. These expected IDs are reference labels for synthetic-case evaluation, not evidence of clinical validity.

### Demonstration Cases

| Case | Expected barrier | Expected task | Intended governance path |
| --- | --- | --- | --- |
| CASE-006 | `transport_timing` | `arrange_transport` | Allowed recommendation, `auto_safe` approval |
| CASE-007 | `med_reconciliation_missing` | `reconcile_meds` | Allowed recommendation, human approval required |

CASE-006 tests a cross-field conflict: transportation is arranged for 18:00, while discharge is planned for the morning. CASE-007 isolates medication reconciliation while the other major discharge arrangements are complete.

### Readable Identifiers

The taxonomy now uses identifiers such as `followup_missing`, `transport_timing`, `schedule_followup`, and `reconcile_meds` instead of opaque codes such as `B-F01` and `T-CM01`.

These remain controlled identifiers used across detection, governance, evaluation, and storage. Governance matches task IDs rather than generated English wording.

## PostgreSQL Persistence

The database separates a synthetic patient case from each execution of the pipeline.

| Table | Stored information |
| --- | --- |
| `patient_cases` | Case ID, condition, source file, patient JSON, and timestamps |
| `pipeline_runs` | Unique run ID, case reference, model/provider, statuses, evaluation JSON, and timestamp |
| `detected_barriers` | Run reference, barrier ID, finding, evidence, priority, confidence, and source field |
| `detected_tasks` | Run reference, task ID, task name, owner role, resolved barrier IDs, priority, and source field |

Running the same case again creates a new `run_id` rather than overwriting the previous execution. The case record itself can be updated, so immutable case-input snapshots and explicit prompt/configuration versions remain future work.

`save_pipeline_run()` commits the related records together and rolls back on a storage error. The pipeline reports database-save errors separately from the analysis result. Database configuration is required at startup because the database module is imported by the pipeline.

Recommendations, governance outcomes, and human-review decisions are not yet stored in dedicated database tables. Human-review decisions currently go to JSONL audit logs.

## Local Setup

Prerequisites: Python with virtual-environment support, Node.js/npm for the frontend, PostgreSQL, and a running Ollama server with the intended MedGemma model available.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Create a local `.env` file with your connection settings. The following database credentials are placeholders:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=medgemma1.5:4b
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/healthcare_agentic_ai
```

Keep credentials out of version control. Ensure the configured PostgreSQL database exists and your Ollama model name matches the installed model shown by `ollama list`.

Create the database tables:

```bash
python3 -m db.init_db
```

### Run a Case

```bash
python3 run_prototype.py data/synthetic/case_006_transport_timing.json
python3 run_prototype.py data/synthetic/case_007_med_review.json
```

CLI results are printed and saved under `results/`, for example `results/case-007_output.json`. This per-case JSON file can be overwritten on a later run; PostgreSQL stores separate execution records. Audit logs are stored under `results/audit_logs/`.

Check the returned `database` status before treating a run as successfully persisted.

### Start the Backend

```bash
python3 -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API documentation: <http://127.0.0.1:8000/docs>

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check backend health |
| `GET /cases` | List synthetic case filenames |
| `POST /cases/{case_filename}/run` | Execute the pipeline for a selected JSON case |
| `POST /reviews` | Record a human-review decision without executing clinical actions |

### Start the Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend uses the backend at `http://127.0.0.1:8000`. The API permits the local Vite origins on port 5173. Use the development-server URL printed by Vite.

## Evaluation

The pipeline compares expected and detected barrier/task IDs and reports:

- **Matched:** expected IDs that were detected.
- **Missed:** expected IDs that were not detected.
- **Extra:** detected IDs absent from the expected labels.

These comparisons support debugging and future aggregate evaluation. They do not establish recommendation quality, clinical safety, or reliable performance across patient populations. Repeated model comparisons and broader case coverage remain planned work.

## Repository Structure

```text
healthcare-agentic-ai/
├── README.md
├── requirements.txt
├── run_prototype.py
├── run_all_cases.py
├── agents/             # Input, analysis, detection, recommendation, and output
├── api/                # FastAPI application and review endpoint
├── db/                 # Database configuration, models, repository, initialization
├── frontend/           # React / TypeScript clinical hub
├── llm/                # Shared Ollama client
├── policy/             # Policy Engine and Approval Gate
├── evaluation/         # Audit logging
├── data/
│   ├── synthetic/      # Seven synthetic cases
│   └── preprocessing/
├── prompts/
├── notebooks/
├── tests/
├── results/
└── docs/               # Literature review and project documentation
```

## Next Steps

- Review professor feedback and refine research priorities.
- Make unknown-task governance consistently require review or block progression.
- Expand governance tests for human-review and forbidden-operation paths.
- Persist recommendations, governance outcomes, and human-review decisions in PostgreSQL.
- Add database-backed run history to the clinical hub.
- Record prompt/configuration versions and immutable case inputs for each experiment.
- Compare models across repeated runs with aggregate detection and governance metrics.
- Expand synthetic case coverage and investigate MIMIC-informed preprocessing and evaluation.

## Future MIMIC Work

- Expand synthetic case coverage
- Add more governance test cases
- Add forbidden-action test scenarios
- Improve recommendation logic
- Add automated evaluation metrics across all cases
- Begin MIMIC-informed preprocessing workflow

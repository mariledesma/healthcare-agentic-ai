# Healthcare Agentic AI

A supervised Agentic AI prototype for hospital discharge coordination.

## Project Goal

This project investigates whether a supervised agentic AI system can identify discharge barriers and pending tasks, generate actionable recommendations, and apply governance and human-approval controls in a structured discharge workflow.

The system is designed as an offline research prototype and is not intended for clinical deployment.

---

## Current Prototype Pipeline

The current prototype implements the following pipeline:

```text
Synthetic Patient JSON
        ↓
Input Reader
        ↓
Case Analyzer
        ↓
Barrier Detector
        ↓
Task Detector
        ↓
Recommendation Agent
        ↓
Policy Engine
        ↓
Approval Gate
        ↓
Audit Logger
        ↓
Output Composer
```

## Component Roles

- **Input Reader**
  - Loads and validates the patient JSON file
  - Checks required fields
  - Rejects malformed or missing input

- **Case Analyzer**
  - Extracts structured clinical context
  - Extracts discharge and social context

- **Barrier Detector**
  - Identifies discharge barriers
  - Maps each barrier to a standardized barrier ID
  - Returns supporting evidence, source field, priority, and confidence

- **Task Detector**
  - Maps detected barriers to pending discharge tasks
  - Assigns task IDs and responsible roles

- **Recommendation Agent**
  - Generates recommended next actions
  - Ranks recommendations by priority
  - Links recommendations back to the barriers they address

- **Policy Engine**
  - Checks whether proposed actions are allowed, forbidden, or require review

- **Approval Gate**
  - Determines whether an action can be safely proposed
  - Flags clinical or discharge-sensitive actions for human approval

- **Audit Logger**
  - Records each step of the pipeline
  - Stores structured JSONL audit logs for traceability

- **Output Composer**
  - Produces the final structured discharge-coordination output

---

## Synthetic Dataset

The prototype currently includes five synthetic discharge cases:

```text
case_001_hf.json
case_002_copd.json
case_003_pneumonia.json
case_004_ortho.json
case_005_stroke.json
```

The cases cover:

- Heart Failure
- COPD
- Pneumonia
- Orthopedic Surgery
- Stroke

Each case includes structured information such as:

- diagnoses
- medications
- laboratory results
- discharge summary
- pending tasks
- transportation status
- caregiver availability
- social barriers
- expected barrier IDs
- expected task IDs
- distractors

The expected barrier and task IDs serve as ground truth for prototype evaluation.

---

## Example Prototype Result

For `CASE-001`, the system identified:

```text
Condition: Heart Failure

Detected Barriers:
B-F01 - Follow-up appointment not scheduled
B-S02 - Transportation not arranged

Detected Tasks:
T-CM01 - Schedule follow-up appointment
T-CM04 - Arrange patient transport
```

The prototype produced:

```text
Expected barriers: 2
Detected barriers: 2
Missed barriers: 0
Extra barriers: 0

Expected tasks: 2
Detected tasks: 2
Missed tasks: 0
Extra tasks: 0
```

The generated recommendations were also passed through the governance layer.

For this case:

```text
Schedule follow-up appointment
Policy: allowed
Approval: auto_safe

Arrange patient transport
Policy: allowed
Approval: auto_safe
```

The final output reported:

```text
Barrier count: 2
Task count: 2
Recommendation count: 2
Human approval required: 0

Final status:
discharge_barriers_present
```

---

## Running the Prototype

From the project directory:

```bash
python3 run_prototype.py data/synthetic/case_001_hf.json
```

To run another case:

```bash
python3 run_prototype.py data/synthetic/case_002_copd.json
```

The output is displayed in the terminal and saved under:

```text
results/
```

For example:

```text
results/case-001_output.json
```

Audit logs are stored under:

```text
results/audit_logs/
```

For example:

```text
results/audit_logs/case-001_audit.jsonl
```

---

## Repository Structure

```text
healthcare-agentic-ai/
├── README.md
├── requirements.txt
├── run_prototype.py
│
├── agents/
│   ├── input_reader.py
│   ├── case_analyzer.py
│   ├── barrier_detector.py
│   ├── task_detector.py
│   ├── recommendation_agent.py
│   ├── safety_agent.py
│   └── output_composer.py
│
├── policy/
│   ├── policy_engine.py
│   └── approval_gate.py
│
├── evaluation/
│   └── audit_logger.py
│
├── data/
│   ├── synthetic/
│   └── preprocessing/
│
├── prompts/
├── notebooks/
├── tests/
├── results/
└── docs/
```

---

## MIMIC Data Sources

Future development will investigate:

- MIMIC-IV v3.1
- MIMIC-IV-Note v2.2
- MIMIC-IV-ED v2.2

Restricted MIMIC data will not be stored in this public repository.

---

## Current Status

### Completed

- GitHub repository structure
- 5 synthetic discharge cases
- Initial recent literature review
- Input Reader
- Case Analyzer
- Barrier Detector
- Task Detector
- Recommendation Agent
- Policy Engine
- Approval Gate
- Audit Logger
- Output Composer
- Structured JSON output
- Ground-truth comparison for barriers and tasks

### Next Steps

- Expand synthetic case coverage
- Add more governance test cases
- Add forbidden-action test scenarios
- Improve recommendation logic
- Add automated evaluation metrics across all cases
- Begin MIMIC-informed preprocessing workflow
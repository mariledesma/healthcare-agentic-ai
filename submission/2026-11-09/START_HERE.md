# Healthcare Agentic AI - Dr. Poudel review package

Prepared for Monday, November 9, 2026. This is a supervisor-review package for a synthetic research prototype, not a completed CVPR manuscript.

## Contents

- `pdf/Poudel_Project_Review.pdf`: four-page overview, backend/database update, measured results, limits and discussion questions.
- `source/`: project source, tests, synthetic data, frozen challenge snapshot and research artifacts.
- `evidence/`: live model response, seven reference run responses, backend validation and final checks.
- `MANIFEST.json`: SHA-256 hashes of included files; relative integrity only, not institutional authentication.

## Review on Maria's existing local setup

The upgraded code is at `/Users/maria/Documents/healthcare-agentic-ai`. The clinical hub is at http://127.0.0.1:5173 and API documentation at http://127.0.0.1:8000/docs.

Open Run History and load the newest CASE-007 run with model `medgemma1.5:4b`. Inspect its source evidence, the human-review requirement, saved review notes and Agent Research. Synthetic validation flags are explicitly marked automated in their notes and are not professor or clinician decisions.

## Start from the supplied source

Prerequisites: Python 3.13-compatible environment, Node.js/npm, PostgreSQL, and Ollama with `medgemma1.5:4b` for live inference. Clean-room installation of all dependencies has not been tested; validation used the working local environment.

```sh
cd source
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your own PostgreSQL connection settings.
# Create the configured database before the migration.
python -m db.migrate
python -m scripts.review_check
python -m uvicorn api.main:app --reload
```

In a second terminal:

```sh
cd source/frontend
npm install
npm run dev
```

To seed a clearly labelled deterministic reference run without inference, from the source root with the Python environment active:

```sh
python run_prototype.py data/synthetic/case_007_med_review.json --offline
```

This command saves a new database run when PostgreSQL is configured. The interface's Run offline reference button instead uses no persistence. Readiness: `GET /ready`. Full live checks: `python -m scripts.review_check --live`.

## Validation and limits

The final passing report is `evidence/final_checks_passed.json`. `evidence/final_checks.json` retains the earlier failure that caught a missing generator-source sync; the source was corrected without rewriting frozen datasets or answer keys. The package also retains the first representation pilot failure and all subsequent frozen experiments rather than deleting unfavorable results.

Tests cover transactions, rollback, migration retries, review identity, retry idempotency, metadata forgery, blocked approvals, audit-file failure and artifact tampering. Live checks verified PostgreSQL persistence, simultaneous review retries and restoration. Learning results are synthetic development results. The learned encoder trails token similarity, and a rule baseline also solves the toy routing MDP.

Actual .env files, credentials, database backups, .git history, virtual environments, node_modules, database dumps and personal audit-log archives are excluded. No real patient dataset is included. The source intentionally has no authenticated reviewer identity or production deployment hardening. No clinical actions are executed.

import os
import logging
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from evaluation.audit_logger import AuditLogger
from run_prototype import run_pipeline


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="Healthcare Agentic AI API",
    version="0.4.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
CASE_DIRECTORY = ROOT_DIRECTORY / "data/synthetic"

audit_logger = AuditLogger()


# =========================================================
# HUMAN REVIEW REQUEST
# =========================================================

# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Healthcare Agentic AI",
        "status": "running",
        "version": "0.4.0"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# LIST AVAILABLE CASES
# =========================================================

@app.get("/cases")
def get_cases():
    cases = []

    for case_file in sorted(
        CASE_DIRECTORY.glob("case_*.json")
    ):
        cases.append(
            {
                "file": case_file.name
            }
        )

    return {
        "count": len(cases),
        "cases": cases
    }


# =========================================================
# RUN PATIENT CASE
# =========================================================

@app.post("/cases/{case_filename}/run")
def run_case(case_filename: str, offline: bool = False, persist: bool = True):

    case_path = (CASE_DIRECTORY / case_filename).resolve()
    if case_path.parent != CASE_DIRECTORY.resolve() or not case_path.name.startswith("case_"):
        raise HTTPException(status_code=400, detail="Invalid case filename")

    if not case_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    if case_path.suffix != ".json":
        raise HTTPException(
            status_code=400,
            detail=(
                "Only JSON case files "
                "are supported"
            )
        )

    try:
        result = run_pipeline(
            str(case_path), use_llm=not offline, persist=persist
        )

        return result

    except Exception as error:
        logging.getLogger(__name__).exception("Pipeline failed for %s", case_filename)
        raise HTTPException(
            status_code=500,
            detail="Pipeline failed; check local server logs"
        )


# =========================================================
# HUMAN REVIEW
# =========================================================

# Durable review and history routes are loaded when database configuration exists.
try:
    from api.storage_routes import router as storage_router
    from api.readiness import check_dependencies
except (ImportError, ValueError):
    storage_router = None
    check_dependencies = None

if storage_router is not None:
    app.include_router(storage_router)


@app.get("/ready")
def ready():
    from fastapi.responses import JSONResponse
    if check_dependencies is None:
        return JSONResponse(status_code=503,content={"status":"not_ready","reason":"Database configuration is missing"})
    result=check_dependencies()
    return JSONResponse(status_code=200 if result['status']=='ready' else 503,content=result)

# Research artifacts are trained offline, frozen, and never confer clinical authority.
from research import service as research_service
from research.provenance import verify as verify_integrity, authenticate
from agents.input_reader import InputReader


class SimulationRequest(BaseModel):
    scenario: Literal["coordination", "clinical", "uncertain", "forbidden"]
    shield: bool = True


class IntegrityRequest(BaseModel):
    manifest: dict
    record: dict
    artifacts: dict


@app.get("/research")
def research_summary():
    try:
        return research_service.summary()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=503, detail="Research bundle is unavailable or failed its integrity check") from error


@app.get("/research/cases/{case_filename}/neighbors")
def research_neighbors(case_filename: str):
    path = (CASE_DIRECTORY / case_filename).resolve()
    if path.parent != CASE_DIRECTORY.resolve() or not path.name.startswith("case_") or path.suffix != ".json":
        raise HTTPException(status_code=400, detail="Invalid case filename")
    loaded = InputReader().read(path)
    if loaded['status'] != 'success':
        raise HTTPException(status_code=404, detail="Case not found or invalid")
    try:
        return research_service.neighbors(loaded['patient_record'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=503, detail="Research bundle is unavailable or invalid") from error


@app.post("/research/simulate")
def research_simulation(request: SimulationRequest):
    try:
        return research_service.simulate(request.scenario, request.shield)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=503, detail="Research bundle is unavailable or invalid") from error


@app.post("/research/verify-integrity")
def research_integrity(request: IntegrityRequest):
    matches = verify_integrity(request.manifest, request.record, request.artifacts)
    return {"matches_manifest": matches,
            "key_holder_authenticated": matches and authenticate(request.manifest, os.getenv("RESEARCH_PROVENANCE_HMAC_KEY")),
            "clinical_truth_verified": False, "execution_performed": False}

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
    version="0.2.0"
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


CASE_DIRECTORY = Path("data/synthetic")

audit_logger = AuditLogger()


# =========================================================
# HUMAN REVIEW REQUEST
# =========================================================

class HumanReviewRequest(BaseModel):
    case_id: str
    recommendation_id: str
    task_id: str
    action: str

    decision: Literal[
        "approved",
        "rejected",
        "flagged"
    ]

    reviewer_role: str = "Research Reviewer"

    notes: Optional[str] = None


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Healthcare Agentic AI",
        "status": "running",
        "version": "0.2.0"
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
def run_case(case_filename: str):

    case_path = (
        CASE_DIRECTORY
        / case_filename
    )

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
            str(case_path)
        )

        return result

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =========================================================
# HUMAN REVIEW
# =========================================================

@app.post("/reviews")
def submit_review(
    review: HumanReviewRequest
):
    """
    Record a human decision about an AI recommendation.

    Important:
    This endpoint records the decision only.

    It does NOT:
    - execute the recommendation
    - modify medications
    - send prescriptions
    - authorize discharge
    - sign clinical documentation
    """

    # -----------------------------------------------------
    # Create readable status
    # -----------------------------------------------------

    if review.decision == "approved":
        review_status = "human_approved"

    elif review.decision == "rejected":
        review_status = "human_rejected"

    else:
        review_status = "human_flagged"


    # -----------------------------------------------------
    # Write decision to the audit log
    # -----------------------------------------------------

    log_entry = audit_logger.log(
        case_id=review.case_id,
        module="HumanReview",
        action=review.action,
        status=review_status,
        details={
            "recommendation_id": (
                review.recommendation_id
            ),
            "task_id": review.task_id,
            "decision": review.decision,
            "reviewer_role": (
                review.reviewer_role
            ),
            "notes": review.notes,
            "execution_performed": False
        }
    )


    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "status": "success",

        "case_id": review.case_id,

        "recommendation_id": (
            review.recommendation_id
        ),

        "task_id": review.task_id,

        "action": review.action,

        "human_review": {
            "decision": review.decision,
            "review_status": review_status,
            "reviewer_role": (
                review.reviewer_role
            ),
            "notes": review.notes
        },

        "execution_performed": False,

        "message": (
            "Human review decision recorded. "
            "No clinical action was executed."
        ),

        "audit_entry": log_entry
    }
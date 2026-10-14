from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException

from run_prototype import run_pipeline


app = FastAPI(
    title="Healthcare Agentic AI API",
    version="0.1.0"
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


@app.get("/")
def root():
    return {
        "name": "Healthcare Agentic AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/cases")
def get_cases():
    cases = []

    for case_file in sorted(
        CASE_DIRECTORY.glob("case_*.json")
    ):
        cases.append({
            "file": case_file.name
        })

    return {
        "count": len(cases),
        "cases": cases
    }


@app.post("/cases/{case_filename}/run")
def run_case(case_filename: str):
    case_path = CASE_DIRECTORY / case_filename

    if not case_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    if case_path.suffix != ".json":
        raise HTTPException(
            status_code=400,
            detail="Only JSON case files are supported"
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
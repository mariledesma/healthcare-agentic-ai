
import argparse
import json
from pathlib import Path

from agents.input_reader import InputReader
from agents.case_analyzer import CaseAnalyzer
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from agents.recommendation_agent import RecommendationAgent
from agents.output_composer import OutputComposer
from agents.readiness_explainer import ReadinessExplainer

from policy.policy_engine import PolicyEngine
from policy.approval_gate import ApprovalGate

from evaluation.audit_logger import AuditLogger
from db.repository import save_pipeline_run


# ---------------------------------------------------------
# Research evaluation helper
# ---------------------------------------------------------

def compare_ids(expected, detected):
    expected_set = set(expected)
    detected_set = set(detected)

    return {
        "expected": expected,
        "detected": detected,
        "matched": sorted(expected_set & detected_set),
        "missed": sorted(expected_set - detected_set),
        "extra": sorted(detected_set - expected_set)
    }


# ---------------------------------------------------------
# Main agentic pipeline
# ---------------------------------------------------------

def run_pipeline(case_file):
    input_reader = InputReader()
    case_analyzer = CaseAnalyzer()
    barrier_detector = BarrierDetector()
    task_detector = TaskDetector()
    recommendation_agent = RecommendationAgent()
    policy_engine = PolicyEngine()
    approval_gate = ApprovalGate()
    output_composer = OutputComposer()
    audit_logger = AuditLogger()

    # -----------------------------------------------------
    # 1. Input Reader
    # -----------------------------------------------------

    input_result = input_reader.read(case_file)

    case_id = input_result.get(
        "patient_record", {}
    ).get("case_id", "UNKNOWN")

    audit_logger.log(
        case_id=case_id,
        module="InputReader",
        action="read_and_validate_case",
        status=input_result["status"],
        details={
            "finding": input_result.get("finding")
        }
    )

    # Stop processing invalid patient records.
    if input_result["status"] != "success":
        return {
            "input_reader": input_result
        }

    # Clinical data is provided to the agents.
    patient_record = input_result["patient_record"]

    # Ground truth is reserved for research evaluation.
    # Remove it from the Input Reader's public output.
    answer_key = input_result.pop("answer_key", {})

    case_id = patient_record["case_id"]

    # -----------------------------------------------------
    # 2. LLM Case Analyzer
    # -----------------------------------------------------

    # Retain standalone model output as unverified research data.
    # Its failure must not prevent the independent deterministic assessment.
    try:
        analysis_result = case_analyzer.analyze(patient_record)
    except Exception as error:
        analysis_result = {
            "agent": "CaseAnalyzer", "status": "error",
            "finding": "Standalone analysis failed; deterministic assessment continues.",
            "error": f"{type(error).__name__}: {error}",
            "llm": case_analyzer.llm.get_metadata()
        }

    audit_logger.log(
        case_id=case_id,
        module="CaseAnalyzer",
        action="analyze_case",
        status=analysis_result["status"],
        details={
            "finding": analysis_result["finding"],
            "llm_provider": analysis_result["llm"]["provider"],
            "llm_model": analysis_result["llm"]["model"],
            "role": "unverified_research_comparison",
            "raw_analysis": analysis_result
        }
    )

    # -----------------------------------------------------
    # 3. Barrier Detector
    # -----------------------------------------------------

    barrier_result = barrier_detector.detect(
        patient_record,
        analysis_result
    )

    barriers = barrier_result["barriers"]

    audit_logger.log(
        case_id=case_id,
        module="BarrierDetector",
        action="detect_barriers",
        status=barrier_result["status"],
        details={
            "barrier_count": len(barriers),
            "barrier_ids": [
                barrier["barrier_id"]
                for barrier in barriers
            ]
        }
    )

    # This explanation uses only detector findings and their actual source values.
    # Rejected model output stays visible, and never replaces detector evidence.
    readiness_explanation = ReadinessExplainer().explain(patient_record, barriers)
    audit_logger.log(
        case_id=case_id, module="ReadinessExplainer", action="explain_detector_evidence",
        status=readiness_explanation["status"],
        details={"requires_review": readiness_explanation["requires_review"],
                 "validation_errors": readiness_explanation["validation_errors"],
                 "detector_evidence": readiness_explanation["detector_evidence"],
                 "raw_response": readiness_explanation["raw_response"],
                 "accepted_explanations": readiness_explanation["explanations"]}
    )

    # -----------------------------------------------------
    # 4. Task Detector
    # -----------------------------------------------------

    task_result = task_detector.detect(
        patient_record,
        barriers
    )

    tasks = task_result["tasks"]

    audit_logger.log(
        case_id=case_id,
        module="TaskDetector",
        action="detect_tasks",
        status=task_result["status"],
        details={
            "task_count": len(tasks),
            "task_ids": [
                task["task_id"]
                for task in tasks
            ]
        }
    )

    # -----------------------------------------------------
    # 5. LLM Recommendation Agent
    # -----------------------------------------------------

    recommendation_result = recommendation_agent.generate(
        barriers,
        tasks
    )

    recommendations = recommendation_result["recommendations"]

    audit_logger.log(
        case_id=case_id,
        module="RecommendationAgent",
        action="generate_recommendations",
        status=recommendation_result["status"],
        details={
            "recommendation_count": len(recommendations),
            "llm_provider": recommendation_result["llm"]["provider"],
            "llm_model": recommendation_result["llm"]["model"]
        }
    )

    # -----------------------------------------------------
    # 6. Governance: Policy Engine + Approval Gate
    # -----------------------------------------------------

    governance_results = []

    for recommendation in recommendations:
        policy_result = policy_engine.evaluate(
            recommendation
        )

        policy_status = policy_result["policy_status"]

        # Forbidden actions are always blocked.
        if policy_status == "forbidden":
            approval_result = {
                "approval_status": "blocked",
                "requires_human_approval": True,
                "task_id": recommendation.get("task_id"),
                "action": recommendation["action"],
                "reason": "Action blocked by the policy engine."
            }

        # Unknown actions must not be automatically approved.
        elif policy_status != "allowed":
            approval_result = {
                "approval_status": "requires_human_approval",
                "requires_human_approval": True,
                "task_id": recommendation.get("task_id"),
                "action": recommendation["action"],
                "reason": (
                    "Action is not explicitly permitted "
                    "and requires human review."
                )
            }

        # Recognized tasks continue to the approval gate.
        else:
            approval_result = approval_gate.evaluate(
                recommendation
            )

        governance_item = {
            "recommendation_id": recommendation["recommendation_id"],
            "task_id": recommendation.get("task_id"),
            "action": recommendation["action"],
            "policy": policy_result,
            "approval": approval_result
        }

        governance_results.append(governance_item)

        audit_logger.log(
            case_id=case_id,
            module="Governance",
            action=recommendation["action"],
            status=policy_status,
            details={
                "recommendation_id": recommendation["recommendation_id"],
                "task_id": recommendation.get("task_id"),
                "policy_status": policy_status,
                "approval_status": approval_result["approval_status"],
                "requires_human_approval": (
                    approval_result["requires_human_approval"]
                )
            }
        )

    # -----------------------------------------------------
    # 7. Output Composer
    # -----------------------------------------------------

    final_output = output_composer.compose(
        patient_record=patient_record,
        barriers=barriers,
        tasks=tasks,
        recommendations=recommendations,
        governance_results=governance_results,
        readiness_explanation=readiness_explanation
    )

    audit_logger.log(
        case_id=case_id,
        module="OutputComposer",
        action="compose_final_output",
        status="success",
        details={
            "final_status": final_output["final_status"]
        }
    )

    # -----------------------------------------------------
    # 8. Offline Research Evaluation
    # -----------------------------------------------------

    expected_barriers = answer_key.get(
        "expected_barriers", []
    )

    expected_tasks = answer_key.get(
        "expected_tasks", []
    )

    detected_barriers = [
        barrier["barrier_id"]
        for barrier in barriers
    ]

    detected_tasks = [
        task["task_id"]
        for task in tasks
    ]

    barrier_evaluation = compare_ids(
        expected_barriers,
        detected_barriers
    )

    task_evaluation = compare_ids(
        expected_tasks,
        detected_tasks
    )

    # -----------------------------------------------------
    # 9. Complete Pipeline Result
    # -----------------------------------------------------

    result = {
        "case_id": case_id,
        "condition": patient_record["condition"],

        "llm_configuration": {
            "case_analyzer": analysis_result["llm"],
            "recommendation_agent": recommendation_result["llm"],
            "readiness_explainer": readiness_explanation["llm"]
        },

        "pipeline": [
            "InputReader",
            "CaseAnalyzer",
            "BarrierDetector",
            "ReadinessExplainer",
            "TaskDetector",
            "RecommendationAgent",
            "PolicyEngine",
            "ApprovalGate",
            "AuditLogger",
            "OutputComposer",
            "PostgreSQLPersistence"
        ],

        "input_reader": input_result,
        "case_analyzer": analysis_result,
        "case_analyzer_role": "unverified_research_comparison",
        "readiness_explanation": readiness_explanation,
        "barrier_detector": barrier_result,
        "task_detector": task_result,
        "recommendation_agent": recommendation_result,

        "governance": {
            "status": "completed",
            "recommendations_reviewed": len(governance_results),
            "results": governance_results
        },

        "final_output": final_output,

        "evaluation": {
            "barriers": barrier_evaluation,
            "tasks": task_evaluation
        }
    }

    # -----------------------------------------------------
    # 10. PostgreSQL Persistence
    # -----------------------------------------------------
    # Database errors are recorded without deleting
    # the results of a completed agent pipeline.

    try:
        database_result = save_pipeline_run(
            patient_record=patient_record,
            result=result,
            source_file=str(case_file)
        )

        result["database"] = database_result

        audit_logger.log(
            case_id=case_id,
            module="PostgreSQL",
            action="save_pipeline_run",
            status="success",
            details={
                "run_id": database_result.get("run_id"),
                "barriers_saved": database_result.get("barriers_saved"),
                "tasks_saved": database_result.get("tasks_saved")
            }
        )

    except Exception as error:
        result["database"] = {
            "status": "error",
            "error": str(error)
        }

        audit_logger.log(
            case_id=case_id,
            module="PostgreSQL",
            action="save_pipeline_run",
            status="error",
            details={
                "error": str(error)
            }
        )

    return result


# ---------------------------------------------------------
# Save results as JSON
# ---------------------------------------------------------

def save_result(result):
    results_directory = Path("results")
    results_directory.mkdir(parents=True, exist_ok=True)

    case_id = result.get("case_id", "unknown_case")

    output_path = (
        results_directory
        / f"{case_id.lower()}_output.json"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    return output_path


# ---------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run the Healthcare Agentic AI pipeline."
    )

    parser.add_argument(
        "case_file",
        help="Path to the synthetic patient JSON file"
    )

    args = parser.parse_args()

    result = run_pipeline(args.case_file)

    output_path = save_result(result)

    print(json.dumps(result, indent=2))
    print(f"\nResult saved to: {output_path}")

    database_result = result.get("database", {})

    if database_result.get("status") == "saved":
        print("\nPostgreSQL:")
        print("Pipeline run saved successfully.")
        print("Run ID:", database_result.get("run_id"))
        print("Barriers saved:", database_result.get("barriers_saved"))
        print("Tasks saved:", database_result.get("tasks_saved"))

    elif database_result:
        print("\nPostgreSQL storage failed:")
        print(database_result.get("error", "Unknown error"))


if __name__ == "__main__":
    main()

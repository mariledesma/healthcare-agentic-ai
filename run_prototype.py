import argparse
import json
from pathlib import Path

from agents.input_reader import InputReader
from agents.case_analyzer import CaseAnalyzer
from agents.barrier_detector import BarrierDetector
from agents.task_detector import TaskDetector
from agents.recommendation_agent import RecommendationAgent
from agents.output_composer import OutputComposer

from policy.policy_engine import PolicyEngine
from policy.approval_gate import ApprovalGate

from evaluation.audit_logger import AuditLogger

from db.repository import save_pipeline_run


# =========================================================
# MAIN PIPELINE
# =========================================================

def run_pipeline(case_file):

    # -----------------------------------------------------
    # Initialize components
    # -----------------------------------------------------

    input_reader = InputReader()

    case_analyzer = CaseAnalyzer()

    barrier_detector = BarrierDetector()

    task_detector = TaskDetector()

    recommendation_agent = RecommendationAgent()

    policy_engine = PolicyEngine()

    approval_gate = ApprovalGate()

    output_composer = OutputComposer()

    audit_logger = AuditLogger()


    # =====================================================
    # 1. INPUT READER
    # =====================================================

    input_result = input_reader.read(
        case_file
    )


    case_id = (
        input_result
        .get(
            "patient_record",
            {}
        )
        .get(
            "case_id",
            "UNKNOWN"
        )
    )


    audit_logger.log(
        case_id=case_id,

        module="InputReader",

        action="read_and_validate_case",

        status=input_result[
            "status"
        ],

        details={
            "finding": input_result.get(
                "finding"
            )
        }
    )


    # Stop the pipeline if the patient
    # file could not be loaded.

    if input_result[
        "status"
    ] != "success":

        return {
            "input_reader": input_result
        }


    patient_record = input_result[
        "patient_record"
    ]


    # =====================================================
    # 2. MEDGEMMA CASE ANALYZER
    # =====================================================

    analysis_result = (
        case_analyzer.analyze(
            patient_record
        )
    )


    audit_logger.log(
        case_id=patient_record[
            "case_id"
        ],

        module="CaseAnalyzer",

        action="analyze_case",

        status=analysis_result[
            "status"
        ],

        details={
            "finding": analysis_result[
                "finding"
            ],

            "llm_provider": (
                analysis_result[
                    "llm"
                ]["provider"]
            ),

            "llm_model": (
                analysis_result[
                    "llm"
                ]["model"]
            )
        }
    )


    # =====================================================
    # 3. BARRIER DETECTOR
    # =====================================================

    barrier_result = (
        barrier_detector.detect(
            patient_record,
            analysis_result
        )
    )


    audit_logger.log(
        case_id=patient_record[
            "case_id"
        ],

        module="BarrierDetector",

        action="detect_barriers",

        status=barrier_result[
            "status"
        ],

        details={
            "barrier_count": len(
                barrier_result[
                    "barriers"
                ]
            ),

            "barrier_ids": [
                barrier[
                    "barrier_id"
                ]

                for barrier
                in barrier_result[
                    "barriers"
                ]
            ]
        }
    )


    # =====================================================
    # 4. TASK DETECTOR
    # =====================================================

    task_result = (
        task_detector.detect(
            patient_record,
            barrier_result[
                "barriers"
            ]
        )
    )


    audit_logger.log(
        case_id=patient_record[
            "case_id"
        ],

        module="TaskDetector",

        action="detect_tasks",

        status=task_result[
            "status"
        ],

        details={
            "task_count": len(
                task_result[
                    "tasks"
                ]
            ),

            "task_ids": [
                task[
                    "task_id"
                ]

                for task
                in task_result[
                    "tasks"
                ]
            ]
        }
    )


    # =====================================================
    # 5. MEDGEMMA RECOMMENDATION AGENT
    # =====================================================

    recommendation_result = (
        recommendation_agent.generate(
            barrier_result[
                "barriers"
            ],

            task_result[
                "tasks"
            ]
        )
    )


    audit_logger.log(
        case_id=patient_record[
            "case_id"
        ],

        module="RecommendationAgent",

        action=(
            "generate_recommendations"
        ),

        status=recommendation_result[
            "status"
        ],

        details={
            "recommendation_count": len(
                recommendation_result[
                    "recommendations"
                ]
            ),

            "llm_provider": (
                recommendation_result[
                    "llm"
                ]["provider"]
            ),

            "llm_model": (
                recommendation_result[
                    "llm"
                ]["model"]
            )
        }
    )


    # =====================================================
    # 6. GOVERNANCE
    # =====================================================

    governance_results = []


    for recommendation in (
        recommendation_result[
            "recommendations"
        ]
    ):

        # ---------------------------------------------
        # Policy Engine
        # ---------------------------------------------

        policy_result = (
            policy_engine.evaluate(
                recommendation
            )
        )


        # ---------------------------------------------
        # Approval Gate
        # ---------------------------------------------

        if (
            policy_result[
                "policy_status"
            ]
            == "forbidden"
        ):

            approval_result = {
                "approval_status": (
                    "blocked"
                ),

                "requires_human_approval": (
                    True
                ),

                "task_id": recommendation.get(
                    "task_id"
                ),

                "action": recommendation[
                    "action"
                ],

                "reason": (
                    "Action was blocked by "
                    "the policy engine."
                )
            }

        else:

            approval_result = (
                approval_gate.evaluate(
                    recommendation
                )
            )


        # ---------------------------------------------
        # Governance Audit Log
        # ---------------------------------------------

        audit_logger.log(
            case_id=patient_record[
                "case_id"
            ],

            module="Governance",

            action=recommendation[
                "action"
            ],

            status=policy_result[
                "policy_status"
            ],

            details={
                "recommendation_id": (
                    recommendation[
                        "recommendation_id"
                    ]
                ),

                "task_id": (
                    recommendation.get(
                        "task_id"
                    )
                ),

                "policy_status": (
                    policy_result[
                        "policy_status"
                    ]
                ),

                "approval_status": (
                    approval_result[
                        "approval_status"
                    ]
                ),

                "requires_human_approval": (
                    approval_result[
                        "requires_human_approval"
                    ]
                )
            }
        )


        governance_results.append(
            {
                "recommendation_id": (
                    recommendation[
                        "recommendation_id"
                    ]
                ),

                "task_id": (
                    recommendation.get(
                        "task_id"
                    )
                ),

                "action": (
                    recommendation[
                        "action"
                    ]
                ),

                "policy": (
                    policy_result
                ),

                "approval": (
                    approval_result
                )
            }
        )


    # =====================================================
    # 7. FINAL OUTPUT COMPOSER
    # =====================================================

    final_output = (
        output_composer.compose(

            patient_record=(
                patient_record
            ),

            barriers=(
                barrier_result[
                    "barriers"
                ]
            ),

            tasks=(
                task_result[
                    "tasks"
                ]
            ),

            recommendations=(
                recommendation_result[
                    "recommendations"
                ]
            ),

            governance_results=(
                governance_results
            )
        )
    )


    audit_logger.log(
        case_id=patient_record[
            "case_id"
        ],

        module="OutputComposer",

        action="compose_final_output",

        status="success",

        details={
            "final_status": (
                final_output[
                    "final_status"
                ]
            )
        }
    )


    # =====================================================
    # 8. BARRIER EVALUATION
    # =====================================================

    expected_barriers = (
        patient_record.get(
            "expected_barriers",
            []
        )
    )


    detected_barriers = [
        barrier[
            "barrier_id"
        ]

        for barrier
        in barrier_result[
            "barriers"
        ]
    ]


    matched_barriers = sorted(
        set(
            expected_barriers
        )
        &
        set(
            detected_barriers
        )
    )


    missed_barriers = sorted(
        set(
            expected_barriers
        )
        -
        set(
            detected_barriers
        )
    )


    extra_barriers = sorted(
        set(
            detected_barriers
        )
        -
        set(
            expected_barriers
        )
    )


    # =====================================================
    # 9. TASK EVALUATION
    # =====================================================

    expected_tasks = (
        patient_record.get(
            "expected_tasks",
            []
        )
    )


    detected_tasks = [
        task[
            "task_id"
        ]

        for task
        in task_result[
            "tasks"
        ]
    ]


    matched_tasks = sorted(
        set(
            expected_tasks
        )
        &
        set(
            detected_tasks
        )
    )


    missed_tasks = sorted(
        set(
            expected_tasks
        )
        -
        set(
            detected_tasks
        )
    )


    extra_tasks = sorted(
        set(
            detected_tasks
        )
        -
        set(
            expected_tasks
        )
    )


    # =====================================================
    # 10. COMPLETE PIPELINE RESULT
    # =====================================================

    result = {

        "case_id": patient_record[
            "case_id"
        ],

        "condition": patient_record[
            "condition"
        ],


        # -------------------------------------------------
        # LLM Configuration
        # -------------------------------------------------

        "llm_configuration": {

            "case_analyzer": (
                analysis_result[
                    "llm"
                ]
            ),

            "recommendation_agent": (
                recommendation_result[
                    "llm"
                ]
            )
        },


        # -------------------------------------------------
        # Pipeline Architecture
        # -------------------------------------------------

        "pipeline": [
            "InputReader",
            "CaseAnalyzer",
            "BarrierDetector",
            "TaskDetector",
            "RecommendationAgent",
            "PolicyEngine",
            "ApprovalGate",
            "AuditLogger",
            "OutputComposer",
            "PostgreSQLPersistence"
        ],


        # -------------------------------------------------
        # Agent Outputs
        # -------------------------------------------------

        "input_reader": (
            input_result
        ),

        "case_analyzer": (
            analysis_result
        ),

        "barrier_detector": (
            barrier_result
        ),

        "task_detector": (
            task_result
        ),

        "recommendation_agent": (
            recommendation_result
        ),


        # -------------------------------------------------
        # Governance
        # -------------------------------------------------

        "governance": {

            "status": "completed",

            "recommendations_reviewed": (
                len(
                    governance_results
                )
            ),

            "results": (
                governance_results
            )
        },


        # -------------------------------------------------
        # Final Output
        # -------------------------------------------------

        "final_output": (
            final_output
        ),


        # -------------------------------------------------
        # Research Evaluation
        # -------------------------------------------------

        "evaluation": {

            "barriers": {

                "expected": (
                    expected_barriers
                ),

                "detected": (
                    detected_barriers
                ),

                "matched": (
                    matched_barriers
                ),

                "missed": (
                    missed_barriers
                ),

                "extra": (
                    extra_barriers
                )
            },


            "tasks": {

                "expected": (
                    expected_tasks
                ),

                "detected": (
                    detected_tasks
                ),

                "matched": (
                    matched_tasks
                ),

                "missed": (
                    missed_tasks
                ),

                "extra": (
                    extra_tasks
                )
            }
        }
    }


    # =====================================================
    # 11. POSTGRESQL PERSISTENCE
    # =====================================================

    try:

        database_result = (
            save_pipeline_run(

                patient_record=(
                    patient_record
                ),

                result=result,

                source_file=str(
                    case_file
                )
            )
        )


        result[
            "database"
        ] = database_result


        # ---------------------------------------------
        # Database Audit Log
        # ---------------------------------------------

        audit_logger.log(
            case_id=patient_record[
                "case_id"
            ],

            module="PostgreSQL",

            action=(
                "save_pipeline_run"
            ),

            status="success",

            details={
                "run_id": (
                    database_result[
                        "run_id"
                    ]
                ),

                "barriers_saved": (
                    database_result[
                        "barriers_saved"
                    ]
                ),

                "tasks_saved": (
                    database_result[
                        "tasks_saved"
                    ]
                )
            }
        )


    except Exception as error:

        # Database failure should not crash
        # the entire agent pipeline.

        result[
            "database"
        ] = {
            "status": "error",
            "error": str(
                error
            )
        }


        audit_logger.log(
            case_id=patient_record[
                "case_id"
            ],

            module="PostgreSQL",

            action=(
                "save_pipeline_run"
            ),

            status="error",

            details={
                "error": str(
                    error
                )
            }
        )


    # =====================================================
    # 12. RETURN COMPLETE RESULT
    # =====================================================

    return result


# =========================================================
# SAVE JSON RESULT
# =========================================================

def save_result(
    result
):

    results_directory = Path(
        "results"
    )


    results_directory.mkdir(
        exist_ok=True
    )


    case_id = result.get(
        "case_id",
        "unknown_case"
    )


    output_path = (
        results_directory
        / f"{case_id.lower()}_output.json"
    )


    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=2
        )


    return output_path


# =========================================================
# COMMAND-LINE ENTRY POINT
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Run the Healthcare Agentic AI "
            "discharge coordination pipeline."
        )
    )


    parser.add_argument(
        "case_file",
        help=(
            "Path to synthetic patient "
            "JSON file"
        )
    )


    args = parser.parse_args()


    # -----------------------------------------------------
    # Run pipeline
    # -----------------------------------------------------

    result = run_pipeline(
        args.case_file
    )


    # -----------------------------------------------------
    # Save JSON copy
    # -----------------------------------------------------

    output_path = save_result(
        result
    )


    # -----------------------------------------------------
    # Print result
    # -----------------------------------------------------

    print(
        json.dumps(
            result,
            indent=2
        )
    )


    print(
        f"\nResult saved to: "
        f"{output_path}"
    )


    # -----------------------------------------------------
    # Database confirmation
    # -----------------------------------------------------

    database_result = (
        result.get(
            "database",
            {}
        )
    )


    if (
        database_result.get(
            "status"
        )
        == "saved"
    ):

        print(
            "\nPostgreSQL:"
        )

        print(
            "Pipeline run saved successfully."
        )

        print(
            "Run ID: "
            f"{database_result.get('run_id')}"
        )

        print(
            "Barriers saved: "
            f"{database_result.get('barriers_saved')}"
        )

        print(
            "Tasks saved: "
            f"{database_result.get('tasks_saved')}"
        )


    elif database_result:

        print(
            "\nPostgreSQL storage failed:"
        )

        print(
            database_result.get(
                "error",
                "Unknown database error"
            )
        )
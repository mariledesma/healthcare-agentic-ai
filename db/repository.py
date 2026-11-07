import uuid
import copy

from sqlalchemy import select, func

from db.database import SessionLocal
from db.models import (
    PatientCase,
    PipelineRun,
    DetectedBarrier,
    DetectedTask, RunArtifact, RecommendationRecord, GovernanceRecord
)


# =========================================================
# SAVE COMPLETE PIPELINE RUN
# =========================================================

def save_pipeline_run(
    patient_record,
    result,
    source_file=None
):
    """
    Save one execution of the AI pipeline.

    The patient case is stored once.
    Every analysis creates a new pipeline run.

    Each detected barrier and task is connected
    to that specific run through run_id.
    """

    session = SessionLocal()

    try:

        case_id = patient_record[
            "case_id"
        ]

        # =================================================
        # 1. STORE OR UPDATE PATIENT CASE
        # =================================================

        values = {"case_id": case_id, "condition": patient_record.get("condition", "Unknown"),
                  "source_file": source_file, "case_data": patient_record}
        if session.bind.dialect.name in ("postgresql", "sqlite"):
            if session.bind.dialect.name == "postgresql":
                from sqlalchemy.dialects.postgresql import insert
            else:
                from sqlalchemy.dialects.sqlite import insert
            statement = insert(PatientCase).values(**values)
            session.execute(statement.on_conflict_do_update(index_elements=[PatientCase.case_id],
                set_={k:values[k] for k in ("condition","source_file","case_data")} | {"updated_at":func.now()}))
        else:
            patient_case = session.get(PatientCase,case_id)
            if patient_case is None: session.add(PatientCase(**values))
            else:
                for key,value in values.items(): setattr(patient_case,key,value)


        # Make sure patient case exists before
        # creating the run that references it.
        session.flush()


        # =================================================
        # 2. CREATE UNIQUE PIPELINE RUN
        # =================================================

        run_id = str(
            uuid.uuid4()
        )


        llm_configuration = (
            result.get(
                "llm_configuration",
                {}
            )
        )


        case_analyzer_llm = (
            llm_configuration.get(
                "case_analyzer",
                {}
            )
        )


        final_output = result.get(
            "final_output",
            {}
        )


        pipeline_run = PipelineRun(
            run_id=run_id,

            case_id=case_id,

            llm_provider=(
                case_analyzer_llm.get(
                    "provider"
                )
            ),

            llm_model=(
                case_analyzer_llm.get(
                    "model"
                )
            ),

            status="completed",

            final_status=(
                final_output.get(
                    "final_status"
                )
            ),

            evaluation=result.get(
                "evaluation"
            )
        )


        session.add(
            pipeline_run
        )


        session.flush()


        # =================================================
        # 3. STORE DETECTED BARRIERS
        # =================================================

        barriers = (
            result
            .get(
                "barrier_detector",
                {}
            )
            .get(
                "barriers",
                []
            )
        )


        for barrier in barriers:

            barrier_record = (
                DetectedBarrier(

                    run_id=run_id,

                    barrier_id=barrier.get(
                        "barrier_id"
                    ),

                    finding=barrier.get(
                        "finding",
                        ""
                    ),

                    evidence=barrier.get(
                        "evidence"
                    ),

                    priority=barrier.get(
                        "priority"
                    ),

                    confidence=barrier.get(
                        "confidence"
                    ),

                    source_field=barrier.get(
                        "source_field"
                    )
                )
            )


            session.add(
                barrier_record
            )


        # =================================================
        # 4. STORE DETECTED TASKS
        # =================================================

        tasks = (
            result
            .get(
                "task_detector",
                {}
            )
            .get(
                "tasks",
                []
            )
        )


        for task in tasks:

            task_record = (
                DetectedTask(

                    run_id=run_id,

                    task_id=task.get(
                        "task_id"
                    ),

                    task_name=task.get(
                        "task_name",
                        ""
                    ),

                    owner_role=task.get(
                        "owner_role"
                    ),

                    resolves_barriers=(
                        task.get(
                            "resolves_barriers",
                            []
                        )
                    ),

                    priority=task.get(
                        "priority"
                    ),

                    source_field=task.get(
                        "source_field"
                    )
                )
            )


            session.add(
                task_record
            )


        # Save normalized proposals/governance and the full immutable response in
        # the same transaction as the case, run, barriers and tasks.
        from research.provenance import digest, verify
        payload = copy.deepcopy(result)
        if not verify(payload["provenance"], patient_record, payload["integrity_artifacts"]):
            raise ValueError("Pipeline provenance does not match the source or artifacts")
        proposals = result.get("recommendation_agent", {}).get("recommendations", [])
        outcomes = result.get("governance", {}).get("results", [])
        proposal_ids = [p["recommendation_id"] for p in proposals]
        if len(set(proposal_ids)) != len(proposal_ids) or set(proposal_ids) != {o["recommendation_id"] for o in outcomes}:
            raise ValueError("Recommendation/governance identities are inconsistent")
        for proposal in proposals:
            session.add(RecommendationRecord(run_id=run_id, recommendation_id=proposal["recommendation_id"],
                task_id=proposal["task_id"], proposal=proposal))
        session.flush()
        for outcome in outcomes:
            session.add(GovernanceRecord(run_id=run_id, recommendation_id=outcome["recommendation_id"],
                policy_status=outcome["policy"]["policy_status"], approval_status=outcome["approval"]["approval_status"],
                outcome=outcome))
        session.add(RunArtifact(run_id=run_id,input_sha256=digest(patient_record),
                                payload_sha256=digest(payload),payload=payload))

        # =================================================
        # 5. COMMIT EVERYTHING
        # =================================================

        session.commit()


        return {
            "status": "saved",
            "run_id": run_id,
            "case_id": case_id,
            "barriers_saved": len(
                barriers
            ),
            "tasks_saved": len(tasks),
            "recommendations_saved": len(proposals), "governance_saved": len(outcomes),
            "artifact_saved": True
        }


    except Exception as error:

        session.rollback()

        raise error


    finally:

        session.close()


# =========================================================
# GET STORED PATIENT CASES
# =========================================================

def get_database_cases():
    """
    Return all patient cases currently stored
    in PostgreSQL.
    """

    session = SessionLocal()

    try:

        statement = (
            select(
                PatientCase
            )
            .order_by(
                PatientCase.case_id
            )
        )


        cases = (
            session
            .scalars(statement)
            .all()
        )


        return [
            {
                "case_id": case.case_id,

                "condition": (
                    case.condition
                ),

                "source_file": (
                    case.source_file
                ),

                "created_at": (
                    case.created_at.isoformat()
                    if case.created_at
                    else None
                ),

                "updated_at": (
                    case.updated_at.isoformat()
                    if case.updated_at
                    else None
                )
            }

            for case in cases
        ]


    finally:

        session.close()


# =========================================================
# GET RECENT PIPELINE RUNS
# =========================================================

def get_recent_runs(
    limit=50
):
    """
    Return the most recent AI pipeline executions.
    """

    session = SessionLocal()

    try:

        statement = (
            select(
                PipelineRun
            )
            .order_by(
                PipelineRun
                .created_at
                .desc()
            )
            .limit(limit)
        )


        runs = (
            session
            .scalars(statement)
            .all()
        )


        return [
            {
                "run_id": (
                    run.run_id
                ),

                "case_id": (
                    run.case_id
                ),

                "llm_provider": (
                    run.llm_provider
                ),

                "llm_model": (
                    run.llm_model
                ),

                "status": (
                    run.status
                ),

                "final_status": (
                    run.final_status
                ),

                "created_at": (
                    run.created_at.isoformat()
                    if run.created_at
                    else None
                )
            }

            for run in runs
        ]


    finally:

        session.close()


# =========================================================
# GET BARRIERS FOR A RUN
# =========================================================

def get_run_barriers(
    run_id
):
    """
    Return barriers associated with one pipeline run.
    """

    session = SessionLocal()

    try:

        statement = (
            select(
                DetectedBarrier
            )
            .where(
                DetectedBarrier.run_id
                == run_id
            )
            .order_by(
                DetectedBarrier.id
            )
        )


        barriers = (
            session
            .scalars(statement)
            .all()
        )


        return [
            {
                "barrier_id": (
                    barrier.barrier_id
                ),

                "finding": (
                    barrier.finding
                ),

                "evidence": (
                    barrier.evidence
                ),

                "priority": (
                    barrier.priority
                ),

                "confidence": (
                    barrier.confidence
                ),

                "source_field": (
                    barrier.source_field
                )
            }

            for barrier in barriers
        ]


    finally:

        session.close()


# =========================================================
# GET TASKS FOR A RUN
# =========================================================

def get_run_tasks(
    run_id
):
    """
    Return tasks associated with one pipeline run.
    """

    session = SessionLocal()

    try:

        statement = (
            select(
                DetectedTask, RunArtifact, RecommendationRecord, GovernanceRecord
            )
            .where(
                DetectedTask.run_id
                == run_id
            )
            .order_by(
                DetectedTask.id
            )
        )


        tasks = (
            session
            .scalars(statement)
            .all()
        )


        return [
            {
                "task_id": (
                    task.task_id
                ),

                "task_name": (
                    task.task_name
                ),

                "owner_role": (
                    task.owner_role
                ),

                "resolves_barriers": (
                    task.resolves_barriers
                ),

                "priority": (
                    task.priority
                ),

                "source_field": (
                    task.source_field
                )
            }

            for task in tasks
        ]


    finally:

        session.close()
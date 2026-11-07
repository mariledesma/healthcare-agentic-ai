from datetime import datetime

from sqlalchemy import (
    Index,
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)

from sqlalchemy.dialects.postgresql import JSONB as PostgreSQLJSONB

# PostgreSQL keeps JSONB; portable JSON enables isolated SQLite contract tests.
JSONB = JSON().with_variant(PostgreSQLJSONB(), "postgresql")

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from db.database import Base


# =========================================================
# PATIENT CASES
# =========================================================

class PatientCase(Base):
    """
    Stores the synthetic patient case itself.

    One patient case can have many pipeline runs.
    """

    __tablename__ = "patient_cases"

    case_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )

    condition: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    source_file: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # Stores the original patient JSON.
    case_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    runs = relationship(
        "PipelineRun",
        back_populates="patient_case",
        cascade="all, delete-orphan"
    )


# =========================================================
# PIPELINE RUNS
# =========================================================

class PipelineRun(Base):
    """
    Stores one execution of the agentic AI pipeline.

    The same patient case can be run many times.
    """

    __tablename__ = "pipeline_runs"
    __table_args__ = (Index("ix_pipeline_runs_created_at_run_id", "created_at", "run_id"),)

    run_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True
    )

    case_id: Mapped[str] = mapped_column(
        ForeignKey(
            "patient_cases.case_id"
        ),
        nullable=False,
        index=True
    )

    llm_provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    llm_model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed"
    )

    final_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # Stores expected/detected/missed/extra results.
    evaluation: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    patient_case = relationship(
        "PatientCase",
        back_populates="runs"
    )

    barriers = relationship(
        "DetectedBarrier",
        back_populates="pipeline_run",
        cascade="all, delete-orphan"
    )

    tasks = relationship(
        "DetectedTask",
        back_populates="pipeline_run",
        cascade="all, delete-orphan"
    )


# =========================================================
# DETECTED BARRIERS
# =========================================================

class DetectedBarrier(Base):
    """
    Stores each barrier detected during a pipeline run.
    """

    __tablename__ = "detected_barriers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "pipeline_runs.run_id"
        ),
        nullable=False,
        index=True
    )

    barrier_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    finding: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    evidence: Mapped[dict | list | str | None] = mapped_column(
        JSONB,
        nullable=True
    )

    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    source_field: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    pipeline_run = relationship(
        "PipelineRun",
        back_populates="barriers"
    )


# =========================================================
# DETECTED TASKS
# =========================================================

class DetectedTask(Base):
    """
    Stores each task generated during a pipeline run.
    """

    __tablename__ = "detected_tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey(
            "pipeline_runs.run_id"
        ),
        nullable=False,
        index=True
    )

    task_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    task_name: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    owner_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    resolves_barriers: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True
    )

    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    source_field: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    pipeline_run = relationship(
        "PipelineRun",
        back_populates="tasks"
    )

class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    revision: Mapped[str] = mapped_column(String(100), primary_key=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunArtifact(Base):
    """Immutable full response before database status is attached; one per run."""
    __tablename__ = "run_artifacts"
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.run_id"), primary_key=True)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecommendationRecord(Base):
    __tablename__ = "recommendation_records"
    __table_args__ = (UniqueConstraint("run_id", "recommendation_id", name="uq_recommendation_run_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("pipeline_runs.run_id"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(250), nullable=False)
    task_id: Mapped[str] = mapped_column(String(150), nullable=False)
    proposal: Mapped[dict] = mapped_column(JSONB, nullable=False)


class GovernanceRecord(Base):
    __tablename__ = "governance_records"
    __table_args__ = (ForeignKeyConstraint(["run_id", "recommendation_id"],
        ["recommendation_records.run_id", "recommendation_records.recommendation_id"], name="fk_governance_recommendation"),
        UniqueConstraint("run_id", "recommendation_id", name="uq_governance_recommendation"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(250), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(100), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)


class HumanReviewRecord(Base):
    """Append-only research decisions. No clinical execution or identity proof."""
    __tablename__ = "human_review_records"
    __table_args__ = (ForeignKeyConstraint(["run_id", "recommendation_id"],
        ["recommendation_records.run_id", "recommendation_records.recommendation_id"], name="fk_review_recommendation"),
        CheckConstraint("decision IN ('approved', 'rejected', 'flagged')", name="ck_review_decision"))
    review_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(250), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(150), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

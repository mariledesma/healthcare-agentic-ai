from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)

from sqlalchemy.dialects.postgresql import JSONB

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
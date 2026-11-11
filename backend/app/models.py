from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint,
    Index, LargeBinary, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

MAX_SEQ_SQL = "9007199254740991"


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    key_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    key_version: Mapped[int] = mapped_column(BigInteger, default=1)
    __table_args__ = (CheckConstraint("key_version >= 1", name="project_key_version"),)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seq: Mapped[int] = mapped_column(BigInteger, default=0)
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="run_project_id"),
        CheckConstraint(f"last_seq BETWEEN 0 AND {MAX_SEQ_SQL}", name="run_seq_bounds"),
        Index("ix_runs_project_id_id", "project_id", "id"),
    )


class MetricEvent(Base):
    __tablename__ = "metric_events"
    run_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column()
    seq: Mapped[int] = mapped_column(BigInteger)
    metric: Mapped[str] = mapped_column(String(64))
    step: Mapped[int] = mapped_column(BigInteger)
    value: Mapped[float] = mapped_column(Float(53))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "run_id"], ["runs.project_id", "runs.id"]),
        UniqueConstraint("run_id", "seq", name="event_run_seq"),
        CheckConstraint(f"seq BETWEEN 1 AND {MAX_SEQ_SQL}", name="event_seq_bounds"),
        CheckConstraint(f"step BETWEEN 0 AND {MAX_SEQ_SQL}", name="event_step_bounds"),
        CheckConstraint("value BETWEEN '-1e308'::float8 AND '1e308'::float8", name="event_value_bounds"),
        CheckConstraint("metric ~ '^[A-Za-z][A-Za-z0-9_.-]{0,63}$'", name="event_metric_name"),
        CheckConstraint("occurred_at >= '2000-01-01 UTC'::timestamptz AND occurred_at < '2100-01-01 UTC'::timestamptz", name="event_time_bounds"),
        Index("ix_events_winner", "project_id", "run_id", "metric", "step", "seq"),
    )


class Batch(Base):
    __tablename__ = "batches"
    run_id: Mapped[UUID] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(primary_key=True)
    project_id: Mapped[UUID] = mapped_column()
    canonical: Mapped[bytes] = mapped_column(LargeBinary)
    digest: Mapped[bytes] = mapped_column(LargeBinary(32))
    receipt: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "run_id"], ["runs.project_id", "runs.id"]),
    )

"""Project keys, runs, append-only metric events and durable batch receipts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("key_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("key_version", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("key_hash"),
        sa.CheckConstraint("key_version >= 1", name="project_key_version"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seq", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "id", name="run_project_id"),
        sa.CheckConstraint("last_seq BETWEEN 0 AND 9007199254740991", name="run_seq_bounds"),
    )
    op.create_index("ix_runs_project_id_id", "runs", ["project_id", "id"])
    op.create_table(
        "metric_events",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("step", sa.BigInteger(), nullable=False),
        sa.Column("value", sa.Float(53), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "event_id"),
        sa.ForeignKeyConstraint(["project_id", "run_id"], ["runs.project_id", "runs.id"]),
        sa.UniqueConstraint("run_id", "seq", name="event_run_seq"),
        sa.CheckConstraint("seq BETWEEN 1 AND 9007199254740991", name="event_seq_bounds"),
        sa.CheckConstraint("step BETWEEN 0 AND 9007199254740991", name="event_step_bounds"),
        sa.CheckConstraint("value BETWEEN '-1e308'::float8 AND '1e308'::float8", name="event_value_bounds"),
        sa.CheckConstraint("metric ~ '^[A-Za-z][A-Za-z0-9_.-]{0,63}$'", name="event_metric_name"),
        sa.CheckConstraint("occurred_at >= '2000-01-01 UTC'::timestamptz AND occurred_at < '2100-01-01 UTC'::timestamptz", name="event_time_bounds"),
    )
    op.create_index("ix_events_winner", "metric_events", ["project_id", "run_id", "metric", "step", "seq"])
    op.create_table(
        "batches",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("canonical", sa.LargeBinary(), nullable=False),
        sa.Column("digest", sa.LargeBinary(32), nullable=False),
        sa.Column("receipt", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("run_id", "batch_id"),
        sa.ForeignKeyConstraint(["project_id", "run_id"], ["runs.project_id", "runs.id"]),
    )


def downgrade():
    op.drop_table("batches")
    op.drop_index("ix_events_winner", table_name="metric_events")
    op.drop_table("metric_events")
    op.drop_index("ix_runs_project_id_id", table_name="runs")
    op.drop_table("runs")
    op.drop_table("projects")

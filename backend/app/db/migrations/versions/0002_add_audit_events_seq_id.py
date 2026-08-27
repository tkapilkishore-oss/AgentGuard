"""Add seq_id autoincrement integer sequence column to audit_events

Revision ID: 0002_add_audit_events_seq_id
Revises: 0001_initial_schema
Create Date: 2026-08-27 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_audit_events_seq_id"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add autoincrement seq_id column to audit_events if not already present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("audit_events")]
    if "seq_id" not in columns:
        op.add_column(
            "audit_events",
            sa.Column(
                "seq_id",
                sa.Integer(),
                sa.Identity(start=1, cycle=False),
                nullable=False,
            ),
        )
        op.create_unique_constraint("uq_audit_events_seq_id", "audit_events", ["seq_id"])
        op.create_index(op.f("ix_audit_events_id"), "audit_events", ["id"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("audit_events")]
    if "seq_id" in columns:
        op.drop_index(op.f("ix_audit_events_id"), table_name="audit_events")
        op.drop_constraint("uq_audit_events_seq_id", "audit_events", type_="unique")
        op.drop_column("audit_events", "seq_id")

"""Receipt replay identity and query indexes; retain all historic rows."""

from alembic import op
import sqlalchemy as sa

revision = "0005_receipt_idempotency"
down_revision = "0004_reliability"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("receipts", sa.Column("command_key", sa.String(64), nullable=True))
    op.create_index("uq_receipt_command", "receipts", ["order_id", "command_key"], unique=True)
    op.create_index("ix_plans_date_status", "plans", ["delivery_date", "status"])
    op.create_index("ix_orders_date_status", "orders", ["delivery_date", "status"])
    # Preflight duplicate published runs; do not silently supersede or delete existing plans.
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT delivery_date FROM plans WHERE status='PUBLISHED' GROUP BY delivery_date HAVING count(*)>1"
            )
        )
        .first()
    )
    if duplicates:
        raise RuntimeError("Resolve multiple published plans for a run before upgrading")
    op.create_index(
        "uq_one_published_plan_per_day",
        "plans",
        ["delivery_date"],
        unique=True,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )


def downgrade():
    raise RuntimeError(
        "Forward-only: preserve receipts and restore a verified backup if rollback is required"
    )

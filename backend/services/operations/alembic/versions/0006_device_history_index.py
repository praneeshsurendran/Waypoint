"""Index bounded actor/device recovery without rewriting evidence or history."""

from alembic import op
import sqlalchemy as sa

revision = "0006_device_history_index"
down_revision = "0005_receipt_idempotency"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_device_operations_device_sequence",
        "device_operations",
        [
            "actor_id",
            sa.text("CAST(payload ->> 'device_id' AS VARCHAR)"),
            sa.text("CAST(payload ->> 'device_sequence' AS INTEGER)"),
        ],
    )


def downgrade():
    raise RuntimeError(
        "Forward-only: preserve device history; use the documented recovery procedure"
    )

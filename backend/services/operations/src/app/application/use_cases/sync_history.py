"""Actor-scoped recovery of committed device acknowledgements, with monotonic paging."""

from sqlalchemy import select
from waypoint_contracts.plan import SyncHistoryEvent, SyncHistoryPage
from app.infrastructure.messaging.models import DeviceCursor, DeviceOperation


def read_history(db, user, device_id, after, limit):
    cursor = db.get(DeviceCursor, (user.id, device_id))
    high_watermark = cursor.sequence if cursor else 0
    sequence = DeviceOperation.payload["device_sequence"].as_integer()
    records = db.scalars(
        select(DeviceOperation)
        .where(
            DeviceOperation.actor_id == user.id,
            DeviceOperation.payload["device_id"].as_string() == device_id,
            sequence > after,
            sequence <= high_watermark,
        )
        .order_by(sequence)
        .limit(limit)
    ).all()
    next_cursor = records[-1].payload["device_sequence"] if records else min(after, high_watermark)
    return SyncHistoryPage(
        device_id=device_id,
        server_cursor=high_watermark,
        next_cursor=next_cursor,
        has_more=next_cursor < high_watermark,
        events=[
            SyncHistoryEvent(
                client_op_id=record.client_op_id,
                device_sequence=record.payload["device_sequence"],
                received_at=record.created_at,
                event=record.payload,
                result=record.response,
            )
            for record in records
        ],
    )

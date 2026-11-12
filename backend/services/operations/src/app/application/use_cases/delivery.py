"""Atomic offline replay with ownership, payload identity, ordering and reconciliation."""

import hashlib
import json
from urllib.parse import urlparse
from fastapi import HTTPException
from sqlalchemy import text
from app.core import clock
from app.infrastructure.db.models.plan import Trip, StopOrder
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.delivery import DeliveryEvent
from app.infrastructure.db.models.reference import Vehicle
from app.infrastructure.messaging.models import DeviceOperation, DeviceCursor, ProofObject
from app.infrastructure.messaging.outbox import enqueue
from app.services.audit import log_action
from app.services.state_machine import transition_order, transition_trip, transition_stop


def fail(code, message, status=409):
    raise HTTPException(status, detail={"code": code, "message": message})


def authorize_trip(db, trip, user):
    if user.role == "DRIVER" and (not user.vehicle_id or trip.vehicle_id != user.vehicle_id):
        fail("FORBIDDEN", "This trip is not assigned to you.", 403)
    vehicle = db.get(Vehicle, trip.vehicle_id)
    if user.role == "LOADER" and (
        not user.depot_id or not vehicle or vehicle.depot_code != user.depot_id
    ):
        fail("FORBIDDEN", "This trip belongs to another depot.", 403)
    if (
        user.role == "DISPATCHER"
        and user.depot_id
        and (not vehicle or vehicle.depot_code != user.depot_id)
    ):
        fail("FORBIDDEN", "This trip belongs to another depot.", 403)


def apply_event(db, stop, body, user):
    if body.stop_id != stop.id:
        fail("STOP_MISMATCH", "Path and event stop IDs must agree.", 422)
    trip = db.get(Trip, stop.trip_id, with_for_update=True)
    authorize_trip(db, trip, user)
    # Serialize the key as well as the trip, including concurrent duplicate posts to different stops.
    if db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": "device-op:" + body.client_op_id},
        )
    payload = body.model_dump(mode="json")
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    previous = db.get(DeviceOperation, body.client_op_id)
    if previous:
        if (
            previous.actor_id != user.id
            or previous.stop_id != stop.id
            or previous.payload_hash != digest
        ):
            fail("IDEMPOTENCY_CONFLICT", "This operation ID already refers to a different event.")
        return {"ok": True, "idempotent": True}
    # Reconcile terminal events written before the device ledger migration.
    legacy = db.query(DeliveryEvent).filter(DeliveryEvent.client_op_id == body.client_op_id).first()
    if legacy:
        if (
            legacy.recorded_by != user.id
            or legacy.stop_id != stop.id
            or legacy.outcome != body.outcome
            or legacy.order_id != body.order_id
        ):
            fail("IDEMPOTENCY_CONFLICT", "Operation conflicts with an earlier delivery record.")
        return {"ok": True, "idempotent": True}
    links = db.query(StopOrder).filter(StopOrder.stop_id == stop.id).all()
    linked = {link.order_id for link in links}
    if body.order_id is not None and body.order_id not in linked:
        fail("ORDER_STOP_MISMATCH", "The order is not part of this stop.", 422)
    if body.device_id is not None:
        if body.device_sequence is None:
            fail("DEVICE_SEQUENCE_REQUIRED", "A device sequence is required.", 422)
        if db.bind.dialect.name == "postgresql":
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"device:{user.id}:{body.device_id}"},
            )
        cursor = db.get(DeviceCursor, (user.id, body.device_id))
        expected = (cursor.sequence if cursor else 0) + 1
        if body.device_sequence != expected:
            fail("SYNC_SEQUENCE_CONFLICT", f"Expected device sequence {expected}.")
        if cursor:
            cursor.sequence = body.device_sequence
        else:
            db.add(
                DeviceCursor(
                    actor_id=user.id, device_id=body.device_id, sequence=body.device_sequence
                )
            )
    paths = [body.pod_photo_path, body.pod_signature_path]
    if body.note and body.note.startswith("/uploads/"):
        paths.append(body.note)
    for path in paths:
        if path:
            parsed = urlparse(path)
            if not parsed.path.startswith("/uploads/"):
                fail("INVALID_PROOF", "Use an uploaded evidence reference.", 422)
            key = parsed.path.removeprefix("/uploads/")
            proof = db.get(ProofObject, key)
            if (
                not proof
                or proof.owner_id != user.id
                or (proof.stop_id is not None and proof.stop_id != stop.id)
            ):
                fail("INVALID_PROOF", "Proof is not owned by this delivery.", 403)
            if proof.stop_id is None:
                proof.stop_id = stop.id
    if stop.status == "FAILED" and body.outcome == "ARRIVED" and body.note == "Retry stop":
        transition_stop(stop, "PENDING")
        for oid in linked:
            order = db.get(Order, oid)
            if order.status == "FAILED":
                order.status = "IN_TRANSIT"
        if trip.status == "COMPLETED":
            trip.status = "IN_TRANSIT"
        log_action(db, "RETRY_STOP", "Stop", stop.id, user.id, after={"status": "PENDING"})
    if stop.status in ("COMPLETED", "PARTIAL", "FAILED"):
        fail(
            "STOP_CONFLICT",
            "The stop has already been finalized; review the server record before retrying.",
        )
    if trip.status not in ("LOADED", "IN_TRANSIT"):
        fail("TRIP_NOT_READY", "The trip must be released before driver actions.")
    now = clock.now()
    if trip.status == "LOADED":
        transition_trip(trip, "IN_TRANSIT")
        for trip_stop in trip.stops:
            for link in trip_stop.stop_orders:
                order = db.get(Order, link.order_id)
                if order.status == "LOADED":
                    transition_order(order, "IN_TRANSIT")
        log_action(db, "START_TRIP", "Trip", trip.id, user.id, after={"status": "IN_TRANSIT"})

    if stop.status == "PENDING" and body.outcome not in ("STARTED", "DELAY"):
        transition_stop(stop, "ARRIVED")
    if body.outcome in ("STARTED", "ARRIVED", "DELAY"):
        if stop.actual_arrival is None and body.outcome == "ARRIVED":
            stop.actual_arrival = now
        if body.outcome == "DELAY":
            enqueue(
                db,
                "delivery.delayed",
                stop.id,
                {**trip_payload(db, trip), "outlet_id": stop.outlet_id, "note": body.note},
            )
    else:
        target = {
            "DELIVERED": "COMPLETED",
            "PARTIAL": "PARTIAL",
            "REFUSED": "FAILED",
            "CLOSED": "FAILED",
            "FAILED": "FAILED",
        }[body.outcome]
        ids = {body.order_id} if body.order_id is not None else linked
        for oid in ids:
            order = db.get(Order, oid)
            target_order = {"DELIVERED": "DELIVERED", "PARTIAL": "PARTIAL"}.get(
                body.outcome, "FAILED"
            )
            if order.status != target_order:
                transition_order(order, target_order)
        # An order-specific event must not hide the other orders at the same outlet.
        remaining = [db.get(Order, oid).status for oid in linked]
        if all(status in ("DELIVERED", "PARTIAL", "FAILED") for status in remaining):
            if any(status == "FAILED" for status in remaining):
                target = "FAILED"
            elif any(status == "PARTIAL" for status in remaining):
                target = "PARTIAL"
            transition_stop(stop, target)
            stop.actual_departure = now
        event = DeliveryEvent(
            stop_id=stop.id,
            order_id=body.order_id,
            outcome=body.outcome,
            note=body.note,
            pod_photo_path=("/uploads/" + urlparse(body.pod_photo_path).path.split("/")[-1])
            if body.pod_photo_path
            else None,
            pod_signature_path=urlparse(body.pod_signature_path).path
            if body.pod_signature_path
            else None,
            receiver_name=body.receiver_name,
            receiver_pin_ok=body.receiver_pin_ok,
            recorded_at=body.recorded_at,
            client_op_id=body.client_op_id,
            recorded_by=user.id,
        )
        db.add(event)
        if all(s.status in ("COMPLETED", "PARTIAL", "FAILED") for s in trip.stops):
            transition_trip(trip, "COMPLETED")
        data = {
            **trip_payload(db, trip),
            "outlet_id": stop.outlet_id,
            "stop_id": stop.id,
            "order_ids": sorted(ids),
            "outcome": body.outcome,
            "recorded_at": body.recorded_at.isoformat() if body.recorded_at else None,
        }
        enqueue(
            db,
            "stop.completed" if body.outcome in ("DELIVERED", "PARTIAL") else "delivery.failed",
            stop.id,
            data,
        )
        if body.outcome in ("DELIVERED", "PARTIAL"):
            enqueue(db, "proof_of_delivery.recorded", stop.id, data)
    db.add(
        DeviceOperation(
            client_op_id=body.client_op_id,
            actor_id=user.id,
            stop_id=stop.id,
            payload_hash=digest,
            payload=payload,
            response={"ok": True},
        )
    )
    log_action(
        db,
        "DELIVERY_EVENT",
        "Stop",
        stop.id,
        user.id,
        after={"outcome": body.outcome, "client_op_id": body.client_op_id},
    )
    return {"ok": True}


def trip_payload(db, trip):
    trip.revision = (trip.revision or 0) + 1
    vehicle = db.get(Vehicle, trip.vehicle_id)
    return {
        "trips": [
            {
                "id": trip.id,
                "vehicle_id": trip.vehicle_id,
                "trip_number": trip.trip_number,
                "status": trip.status,
                "revision": trip.revision,
            }
        ],
        "vehicle_id": trip.vehicle_id,
        "depot_id": vehicle.depot_code if vehicle else None,
        "revision": trip.revision,
    }

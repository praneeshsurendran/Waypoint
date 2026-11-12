"""Pure workflow transitions; transport error mapping lives in the service adapter."""


class InvalidTransition(ValueError):
    def __init__(self, current, attempted, allowed):
        self.current = current
        self.attempted = attempted
        self.allowed = sorted(allowed)
        super().__init__(f"Cannot move from {current!r} to {attempted!r}.")


def transition(entity, new_status, transitions):
    allowed = transitions.get(entity.status, set())
    if new_status not in allowed:
        raise InvalidTransition(entity.status, new_status, allowed)
    entity.status = new_status


ORDER_TRANSITIONS: dict[str, set[str]] = {
    "PLACED": {"CONFIRMED", "QUEUED", "CANCELLED"},
    "CONFIRMED": {"QUEUED", "CANCELLED", "DEFERRED", "PLANNED"},
    "QUEUED": {"PLANNED", "CANCELLED", "DEFERRED"},
    "PLANNED": {"LOADED", "DEFERRED", "CANCELLED", "QUEUED"},
    "LOADED": {"IN_TRANSIT", "DELIVERED", "PARTIAL", "FAILED", "CANCELLED"},
    "IN_TRANSIT": {"DELIVERED", "PARTIAL", "FAILED", "DEFERRED"},
    "DELIVERED": {"PARTIAL"},  # receipt dispute
    "PARTIAL": set(),
    "FAILED": {"DEFERRED", "CANCELLED"},
    "DEFERRED": {"QUEUED", "CONFIRMED", "CANCELLED"},
    "CANCELLED": set(),
}

TRIP_TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"LOADING", "LOADED", "CANCELLED"},
    "LOADING": {"LOADED", "CANCELLED"},
    "LOADED": {"IN_TRANSIT", "COMPLETED", "CANCELLED"},
    "IN_TRANSIT": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

STOP_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"ARRIVED"},
    "ARRIVED": {"COMPLETED", "PARTIAL", "FAILED"},
    "COMPLETED": set(),
    "PARTIAL": set(),
    "FAILED": {"PENDING"},  # retry
}

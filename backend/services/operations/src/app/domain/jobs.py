from dataclasses import dataclass
from datetime import date


@dataclass
class Job:
    id: str
    request_key: str
    delivery_date: date
    requested_by: int
    status: str = "pending"
    plan_id: int | None = None
    error_code: str | None = None

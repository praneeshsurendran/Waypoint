import datetime as dt
import uuid
from pydantic import Field
from waypoint_contracts.common import ContractModel as BaseModel


class JobRequest(BaseModel):
    delivery_date: dt.date
    request_key: str = Field(
        default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=100
    )

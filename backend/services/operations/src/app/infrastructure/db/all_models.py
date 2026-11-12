# Import all models here so Alembic's env.py can discover them via Base.metadata
from app.infrastructure.db.base import Base  # noqa: F401
from app.infrastructure.db.models.user import User  # noqa: F401
from app.infrastructure.db.models.order import Order, OrderLine  # noqa: F401
from app.infrastructure.db.models.plan import Plan, Trip, Stop, StopOrder  # noqa: F401
from app.infrastructure.db.models.deferral import Deferral  # noqa: F401
from app.infrastructure.db.models.loading import LoadCheck  # noqa: F401
from app.infrastructure.db.models.delivery import DeliveryEvent  # noqa: F401
from app.infrastructure.db.models.receipt import Receipt  # noqa: F401
from app.infrastructure.db.models.issue import Issue  # noqa: F401
from app.infrastructure.db.models.notification import Notification  # noqa: F401
from app.infrastructure.db.models.audit import AuditLog  # noqa: F401

from app.infrastructure.messaging import models as messaging_models  # noqa: F401

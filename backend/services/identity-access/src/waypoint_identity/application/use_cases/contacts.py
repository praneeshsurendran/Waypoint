from pydantic import TypeAdapter
from waypoint_contracts.runtime import ManagerContact
from sqlalchemy.orm import Session as DbDep
from waypoint_identity.infrastructure.db.accounts import User


def list_store_managers(db: DbDep, _: object = None) -> list[ManagerContact]:
    """Who receives at each outlet, so a driver or dispatcher can call ahead. Names and phones only."""
    managers = (
        db.query(User)
        .filter(
            User.role == "STORE_MANAGER",
            User.is_active.is_(True),
            User.outlet_id.isnot(None),
        )
        .all()
    )
    return TypeAdapter(list[ManagerContact]).validate_python(
        [
            {
                "id": m.id,
                "full_name": m.full_name,
                "phone": m.phone,
                "outlet_id": m.outlet_id,
            }
            for m in managers
        ]
    )

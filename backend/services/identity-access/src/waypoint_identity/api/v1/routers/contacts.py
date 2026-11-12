from pydantic import TypeAdapter
from waypoint_contracts.runtime import ManagerContact
from fastapi import APIRouter
from waypoint_identity.api.dependencies import DbDep, require_role
from waypoint_identity.application.use_cases import contacts as use_cases

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get(
    "/store-managers",
    response_model=list[ManagerContact],
    response_model_exclude_unset=True,
)
def list_store_managers(
    db: DbDep, _: object = require_role("DISPATCHER", "DRIVER", "LOADER")
) -> list[ManagerContact]:
    """Who receives at each outlet, so a driver or dispatcher can call ahead. Names and phones only."""
    return TypeAdapter(list[ManagerContact]).validate_python(
        use_cases.list_store_managers(db=db, _=_)
    )

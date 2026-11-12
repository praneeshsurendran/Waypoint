from fastapi.params import Depends as Dependency
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from waypoint_security import Principal, verified_principal
from waypoint_network.bootstrap import get_db

DbDep = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[Principal, Depends(verified_principal)]


def require_role(*roles: str) -> Dependency:
    def check(user: CurrentUser) -> Principal:
        if user.role not in roles:
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "Role not permitted."}
            )
        return user

    return Depends(check)

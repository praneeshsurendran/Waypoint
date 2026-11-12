from typing import Protocol
from app.domain.planning.types import PlannerContext, PlannerPlan


class AllocationStrategy(Protocol):
    def allocate(self, context: PlannerContext) -> PlannerPlan: ...

"""Reproducible synthetic PostgreSQL aggregation measurement in a disposable database."""

import datetime as dt
import json
import os
import statistics
import time
import tracemalloc
from uuid import uuid4

from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.infrastructure.db.base import Base
import app.infrastructure.db.all_models  # noqa: F401
from app.infrastructure.db.models.order import Order
from app.infrastructure.db.models.reference import Depot, Outlet


def main() -> None:
    url = os.environ["PERFORMANCE_DATABASE_URL"]
    if not (make_url(url).database or "").endswith("_test"):
        raise RuntimeError("Only a disposable _test database may be benchmarked")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    day = dt.date(2035, 1, 2)
    key = uuid4().hex[:10]
    with Session(engine) as db:
        db.add(Depot(code=key, name="Synthetic benchmark"))
        db.flush()
        db.add(
            Outlet(
                outlet_id=key,
                brand="Fresh",
                district="Synthetic",
                depot_code=key,
                dock_type="street",
                van_only=False,
                is_mall=False,
            )
        )
        db.flush()
        db.execute(
            insert(Order),
            [
                {
                    "reference": f"{key}-{i}",
                    "outlet_id": key,
                    "brand": "Fresh",
                    "temperature_class": "CHILLED",
                    "delivery_date": day,
                    "status": ("CONFIRMED", "DELIVERED", "DEFERRED")[i % 3],
                    "total_weight": 50.0,
                    "total_volume": 1.0,
                    "total_cases": 10,
                }
                for i in range(10000)
            ],
        )
        db.flush()
        old = select(Order).where(Order.delivery_date == day)
        new = (
            select(Order.status, func.count(Order.id))
            .where(Order.delivery_date == day)
            .group_by(Order.status)
        )

        def measure(grouped: bool) -> dict:
            timings = []
            peak = 0
            counts = {}
            for _ in range(5):
                db.expunge_all()
                tracemalloc.start()
                started = time.perf_counter()
                if grouped:
                    rows = db.execute(new).all()
                    counts = {status: count for status, count in rows}
                else:
                    orders = db.scalars(old).all()
                    counts = {}
                    for order in orders:
                        counts[order.status] = counts.get(order.status, 0) + 1
                timings.append((time.perf_counter() - started) * 1000)
                peak = max(peak, tracemalloc.get_traced_memory()[1])
                tracemalloc.stop()
            return {
                "median_ms": round(statistics.median(timings), 3),
                "peak_python_bytes": peak,
                "counts": counts,
                "rows_transferred": len(counts) if grouped else sum(counts.values()),
            }

        before, after = measure(False), measure(True)
        assert before["counts"] == after["counts"]

        def explain(statement):
            sql = str(statement.compile(engine, compile_kwargs={"literal_binds": True}))
            return db.execute(
                text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
            ).scalar_one()

        print(
            json.dumps(
                {
                    "scope": "10000 synthetic orders, five samples, same transaction and existing indexes; local wall time includes Python materialization",
                    "before": before,
                    "after": after,
                    "plans": {"before": explain(old), "after": explain(new)},
                },
                default=str,
            )
        )
        db.rollback()
    engine.dispose()


if __name__ == "__main__":
    main()

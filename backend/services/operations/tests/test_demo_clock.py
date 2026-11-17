"""A walkthrough is reproducible without overriding the production clock."""

import datetime as dt
from types import SimpleNamespace
from app.core import clock


def test_fixed_demo_time_is_explicit_and_production_uses_real_time(monkeypatch):
    settings = SimpleNamespace(
        demo_mode=True,
        demo_time=dt.time(9, 15),
        business_date="2026-02-15",
        demo_delivery_date="2026-02-16",
    )
    monkeypatch.setattr(clock, "get_settings", lambda: settings)
    assert clock.now() == dt.datetime(
        2026, 2, 15, 9, 15, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30))
    )
    assert not clock.is_past_cutoff()
    settings.demo_time = dt.time(16, 1)
    assert clock.is_past_cutoff()
    settings.demo_mode = False
    assert abs((clock.now() - dt.datetime.now(dt.timezone.utc)).total_seconds()) < 2

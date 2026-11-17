"""Check temporal information boundaries and adversarial allocation failures."""

import unittest
import numpy as np
import pandas as pd
from task2a import history, examples
from task2b import inputs, allocation, validate, trip_minutes


class ForecastTests(unittest.TestCase):
    def test_future_outcomes_cannot_change_features(self):
        panel, wc, last = history()
        origin = 64
        a = examples(panel, wc, [origin])
        changed = panel.copy()
        changed.loc[changed.week_idx > origin, "volume"] = 123456.0
        b = examples(changed, wc, [origin])
        pd.testing.assert_frame_equal(
            a.drop(columns="volume"), b.drop(columns="volume")
        )
        self.assertFalse(np.allclose(a.volume, b.volume))


class AllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = inputs()
        cls.orders, cls.fleet, cls.travel, cls.allowance = cls.context

    def errors(self, assignment):
        return validate(allocation(self.orders, assignment), *self.context)["errors"]

    def test_workshop_and_temperature(self):
        chilled = int(self.orders.index[self.orders.temp_requirement.eq("chilled")][0])
        ambient = (
            self.fleet[
                self.fleet.status.eq("available") & self.fleet.temp.eq("ambient")
            ]
            .iloc[0]
            .vehicle_id
        )
        workshop = self.fleet[self.fleet.status.eq("in_workshop")].iloc[0].vehicle_id
        self.assertTrue(
            any("chilled on ambient" in e for e in self.errors({chilled: (ambient, 1)}))
        )
        self.assertTrue(
            any("workshop" in e for e in self.errors({chilled: (workshop, 1)}))
        )

    def test_van_access_and_oversize(self):
        truck = (
            self.fleet[self.fleet.status.eq("available") & self.fleet.type.eq("truck")]
            .sort_values("volume_cap_m3")
            .iloc[-1]
            .vehicle_id
        )
        access = int(
            self.orders.index[self.orders.parking_constraint.eq("van_only")][0]
        )
        large = int(self.orders.index[self.orders.order_ref.eq("S1-078")][0])
        self.assertTrue(
            any("truck at van-only" in e for e in self.errors({access: (truck, 1)}))
        )
        self.assertTrue(
            any("volume exceeded" in e for e in self.errors({large: (truck, 1)}))
        )

    def test_separate_orders_count_as_separate_stops(self):
        rows = self.orders[self.orders.outlet_id.eq("OUT001")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            trip_minutes(rows, self.travel, self.allowance), 24 + 8 + 16 + 16
        )

    def test_no_third_trip_and_no_mixed_group(self):
        vehicle = self.fleet[self.fleet.status.eq("available")].iloc[0].vehicle_id
        self.assertTrue(
            any("trip must be" in e for e in self.errors({0: (vehicle, 3)}))
        )
        style = int(self.orders.index[self.orders.brand.eq("Style")][0])
        self.assertTrue(
            any(
                "mixed brand/district" in e
                for e in self.errors({0: (vehicle, 1), style: (vehicle, 1)})
            )
        )


if __name__ == "__main__":
    unittest.main()

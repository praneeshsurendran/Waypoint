import unittest
import tempfile
import numpy as np
from catboost import CatBoostRegressor
from sklearn.isotonic import IsotonicRegression
from features import prepare_task1, minutes
from task1 import predict


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train = prepare_task1()
        cls.test = prepare_task1(True)

    def test_labels_exclude_waiting(self):
        d = self.train
        early = minutes(d.arrival_time) < minutes(d.window_open_time)
        self.assertEqual(int(early.sum()), 4023)
        np.testing.assert_array_equal(
            d.loc[early, "service"],
            minutes(d.loc[early, "leave_outlet_time"])
            - minutes(d.loc[early, "window_open_time"]),
        )
        np.testing.assert_array_equal(
            d.late, (minutes(d.arrival_time) > minutes(d.window_close_time)).astype(int)
        )

    def test_row_keys_and_counts(self):
        self.assertEqual(len(self.train), 91894)
        self.assertEqual(len(self.test), 5014)
        self.assertFalse(self.train.delivery_id.duplicated().any())
        self.assertFalse(self.test.delivery_id.duplicated().any())
        self.assertEqual(
            set(self.train.delivery_id) & set(self.test.delivery_id), set()
        )

    def test_calibration_applies_to_blend(self):
        a = {"kind": "baseline", "task": "late", "default": 0.2}
        b = {"kind": "baseline", "task": "late", "default": 0.4}
        cal = IsotonicRegression(out_of_bounds="clip").fit([0.0, 1.0], [0.1, 0.9])
        bundle = {
            "kind": "blend",
            "task": "late",
            "components": [(0.5, a), (0.5, b)],
            "calibration": ("isotonic", cal),
        }
        np.testing.assert_allclose(predict(bundle, self.test.head()), 0.34)

    def test_prefixes_exclude_current_stop(self):
        first = self.train[self.train.seq.eq(0)]
        self.assertTrue(first.prefix_order_volume_m3.eq(0).all())
        self.assertTrue(first.prefix_service_allowance_min.eq(0).all())


class SnapshotTests(unittest.TestCase):
    def test_extended_snapshot_matches_uninterrupted_training(self):
        x = np.arange(240).reshape(120, 2)
        y = np.sin(x[:, 0] / 20)
        with tempfile.TemporaryDirectory() as directory:
            params = dict(
                depth=2,
                learning_rate=0.03,
                random_seed=42,
                thread_count=1,
                train_dir=directory,
            )
            for cap in [5, 10]:
                resumed = CatBoostRegressor(iterations=cap, **params)
                resumed.fit(
                    x,
                    y,
                    eval_set=(x, y),
                    use_best_model=False,
                    verbose=False,
                    save_snapshot=True,
                    snapshot_file=directory + "/recovery",
                )
            direct = CatBoostRegressor(iterations=10, **params)
            direct.fit(x, y, verbose=False)
            self.assertEqual(resumed.tree_count_, 10)
            self.assertEqual(len(resumed.get_evals_result()["validation"]["RMSE"]), 10)
            np.testing.assert_allclose(
                resumed.predict(x), direct.predict(x), rtol=1e-12, atol=1e-12
            )


if __name__ == "__main__":
    unittest.main()

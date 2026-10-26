import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / "app/data/prepare_training_next.py"
spec = importlib.util.spec_from_file_location("prepare_training_next", script)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class TrainingPreparationTests(unittest.TestCase):
    def row(self, key, group, location="Hải Châu"):
        return dict(record_key=key, pipeline_group=group, location_feature=location, price_million="3000")

    def test_quarantines_invalid_location_without_relabelling_kept_rows(self):
        valid, invalid = self.row("a", "g1"), self.row("b", "g2", "new_unit:ban nha rieng")
        kept, quarantine = prep.partition([valid, invalid], [self.row("c", "g3")], {"Hải Châu"})
        self.assertEqual(kept, [valid])
        self.assertEqual(quarantine[0]["record_key"], "b")
        self.assertEqual(valid["price_million"], "3000")
        self.assertNotIn("quarantine_reason", invalid)

    def test_rejects_duplicate_ids_and_group_leakage(self):
        for train, val in (([self.row("a", "g1"), self.row("a", "g1")], []),
                           ([self.row("a", "g1")], [self.row("a", "g2")]),
                           ([self.row("a", "g1")], [self.row("b", "g1")])):
            with self.subTest(train=train, validation=val), self.assertRaises(ValueError):
                prep.partition(train, val, {"Hải Châu"})

    def test_does_not_silently_drop_an_unreviewed_validation_case(self):
        with self.assertRaisesRegex(ValueError, "new evaluation protocol"):
            prep.partition([self.row("a", "g1")], [self.row("b", "g2", "unknown")], {"Hải Châu"})


if __name__ == "__main__":
    unittest.main()

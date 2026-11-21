import unittest

from origen.v324_rolling_memory import RollingPartitionModel


class TestV324RollingMemory(unittest.TestCase):
    def test_remove_reverses_update_and_preserves_normalization(self):
        model = RollingPartitionModel()
        draws = ([1, 2, 3, 4, 5], [6, 9, 12, 20, 28], [2, 7, 13, 19, 25])
        for draw in draws:
            model.update(draw)
        before = model.probabilities().copy()
        model.remove(draws[0])
        self.assertEqual(model.draws_seen, 2)
        self.assertAlmostEqual(float(model.probabilities().sum()), 1.0, places=12)
        self.assertNotEqual(float(before[0]), float(model.probabilities()[0]))

    def test_remove_rejects_underflow_and_unknown_draw(self):
        model = RollingPartitionModel()
        with self.assertRaises(ValueError):
            model.remove([1, 2, 3, 4, 5])
        model.update([1, 2, 3, 4, 5])
        with self.assertRaises(ValueError):
            model.remove([6, 7, 8, 9, 10])
        model.remove([1, 2, 3, 4, 5])
        self.assertEqual(model.draws_seen, 0)
        self.assertAlmostEqual(float(model.probabilities().sum()), 1.0, places=12)

    def test_remove_rejects_boolean_numbers(self):
        model = RollingPartitionModel()
        with self.assertRaises(ValueError):
            model.remove([True, 2, 3, 4, 5])


if __name__ == "__main__":
    unittest.main()

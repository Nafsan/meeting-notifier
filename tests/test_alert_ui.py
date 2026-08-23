import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alert_ui import _round_rect_points


class RoundRectPointsTests(unittest.TestCase):
    def test_returns_12_points_as_24_coordinates(self):
        points = _round_rect_points(0, 0, 100, 50, 10)
        self.assertEqual(len(points), 24)

    def test_points_stay_within_the_bounding_box(self):
        x1, y1, x2, y2, r = 10, 20, 110, 70, 15
        points = _round_rect_points(x1, y1, x2, y2, r)
        xs = points[0::2]
        ys = points[1::2]

        self.assertTrue(all(x1 <= x <= x2 for x in xs))
        self.assertTrue(all(y1 <= y <= y2 for y in ys))


if __name__ == "__main__":
    unittest.main()

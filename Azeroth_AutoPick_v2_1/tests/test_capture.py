import unittest
from autopick.capture import group_cards

class CaptureTests(unittest.TestCase):
    def test_three_columns_and_row_order(self):
        lines = [(0.51, 0.25, "Fireball", 0.98),
                 (0.18, 0.21, "Blizzard", 0.98),
                 (0.82, 0.21, "Flamestrike", 0.98),
                 (0.51, 0.10, "2", 0.94)]
        cards = group_cards(lines, 3)
        self.assertEqual(cards, [["Blizzard"], ["2", "Fireball"], ["Flamestrike"]])

    def test_four_columns(self):
        cards = group_cards([(0.10, 0.1, "A", 1.0), (0.38, 0.1, "B", 1.0),
                             (0.62, 0.1, "C", 1.0), (0.89, 0.1, "D", 1.0)], 4)
        self.assertEqual(cards, [["A"], ["B"], ["C"], ["D"]])

if __name__ == "__main__":
    unittest.main()

import unittest
from autopick.engine import best_choice, card_fingerprint, match_quality, popup_hint

class SelectionTests(unittest.TestCase):
    def test_first_matching_priority_wins(self):
        cards = [["1", "Frostbolt", "Rank II"], ["2", "Fireball", "Rank III"], ["3", "Blizzard", "Rank I"]]
        d = best_choice("level", cards, ["Fireball", "Blizzard"], [])
        self.assertEqual(d.index, 2)
        self.assertEqual(d.rule, "Fireball")

    def test_description_does_not_take_priority(self):
        cards = [["1", "Conjure Food", "Summon food that restores mana", "Fireball is improved"],
                 ["2", "Consecration", "Area damage"], ["3", "Holy Light"]]
        d = best_choice("level", cards, ["Consecration", "Fireball"], [])
        self.assertEqual(d.index, 2)

    def test_ignores_name_only_in_description(self):
        cards = [["1", "Conjure Food", "Rare", "Fireba11 improves nearby units"],
                 ["2", "Frostbolt"], ["3", "Blizzard"]]
        self.assertIsNone(best_choice("level", cards, ["Fireball"], []))

    def test_multiline_jewelry(self):
        cards = [["1", "Heavy Dark Iron Ring"],
                 ["2", "Archimtiros' Ring", "of Reckoning"],
                 ["3", "Hand of Justice"]]
        d = best_choice("loot", cards, ["Archimtiros' Ring of Reckoning", "Hand of Justice"], [])
        self.assertEqual(d.index, 2)

    def test_avoid_preference(self):
        cards = [["1", "Fireball"], ["2", "Blizzard"], ["3", "Frostbolt"]]
        d = best_choice("level", cards, ["Fireball", "Blizzard"], ["Fireball"])
        self.assertEqual(d.index, 2)

    def test_no_match_waits(self):
        self.assertIsNone(best_choice("loot", [["Ring A"], ["Ring B"], ["Ring C"]], ["Choker of Enlightenment"], []))

    def test_opt_in_fallback(self):
        d = best_choice("loot", [["Ring A"], ["Ring B"], ["Ring C"]], ["Choker of Enlightenment"], [], fallback="first")
        self.assertEqual(d.index, 1)

    def test_no_fallback_on_unreadable_cards(self):
        d = best_choice("level", [["Firebolt"], [], ["Blizzard"]], [], [], fallback="first")
        self.assertIsNone(d)

    def test_short_names_exact(self):
        self.assertEqual(match_quality("Fear", ["Feral Charge"]), 0.0)
        self.assertEqual(match_quality("Fear", ["Fear"]), 1.0)

    def test_popup_hint(self):
        self.assertEqual(popup_hint("Level Up! Choose an ability"), "level")
        self.assertEqual(popup_hint("Guardian's Lair: Choose Jewellery"), "loot")
        self.assertIsNone(popup_hint("Elwynn Forest 17:24 Kills: 100"))

    def test_fingerprint_changes(self):
        a = card_fingerprint("level", [["Fireball"], ["Blizzard"]])
        b = card_fingerprint("level", [["Arcane Missiles"], ["Blizzard"]])
        self.assertNotEqual(a, b)

if __name__ == "__main__":
    unittest.main()

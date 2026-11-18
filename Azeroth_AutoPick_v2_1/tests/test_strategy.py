import unittest

from autopick.strategy import (
    Action, Controls, RARITIES, action_fingerprint, detect_rarity,
    parse_banish_count, parse_free_rerolls, parse_offers, select_action,
)


class StrategyTests(unittest.TestCase):
    @staticmethod
    def offer(*rows):
        return parse_offers(rows)

    def test_screenshot_one_uses_only_free_reroll(self):
        cards = self.offer(
            ["UNCOMMON", "Hammer of Wrath", "New spell"],
            ["COMMON", "Redemption", "New spell"],
            ["COMMON", "Exorcism", "New spell"],
        )
        d = select_action("level", cards, Controls("Reroll 4", "Skip +11 gold"),
                          ["Consecration", "Divine Shield", "Holy Shield"], [], [], min_rarity="Rare")
        self.assertEqual(d.kind, "reroll")

    def test_screenshot_two_skip_paid_reroll_even_if_preferred(self):
        cards = self.offer(
            ["COMMON", "Consecration", "Rank 7 > 8"],
            ["COMMON", "Hammer of Justice", "Rank 2 > 3"],
            ["COMMON", "Hammer of Wrath", "New spell"],
        )
        d = select_action("level", cards, Controls("Reroll 100 gold", "Skip +11 gold"),
                          ["Consecration", "Holy Shield"], [], [], min_rarity="Uncommon")
        self.assertEqual(d.kind, "skip")

    def test_pick_wins_over_banish_and_reroll(self):
        cards = self.offer(
            ["Epic", "Hand of Justice"], ["Common", "Carrot on a Stick"],
            ["Rare", "Lifegiving Gem"],
        )
        controls = Controls("Reroll 3", "Skip +15 gold", ("Banish (2)",) * 3)
        d = select_action("loot", cards, controls, ["Hand of Justice", "Lifegiving Gem"], [],
                          ["Carrot on a Stick"], min_rarity="Rare")
        self.assertEqual((d.kind, d.index), ("pick", 1))

    def test_can_banish_explicit_jewelry_name_if_nothing_eligible(self):
        cards = self.offer(
            ["Common", "Carrot on a Stick"], ["Common", "Onyxia Blood Talisman"],
            ["Rare", "Gnomish Universal Remote"],
        )
        controls = Controls("Reroll 2", "Skip +5 gold", ("Banish (2)",) * 3)
        d = select_action("loot", cards, controls, ["Hand of Justice"], [],
                          ["Carrot on a Stick"], min_rarity="Rare")
        self.assertEqual((d.kind, d.index), ("banish", 1))

    def test_no_banish_without_charges(self):
        cards = self.offer(["Common", "Carrot on a Stick"], ["Common", "Gold Ring"], ["Common", "Silver Ring"])
        d = select_action("loot", cards, Controls("Reroll 2", "Skip +10 gold", ("Banish (0)",) * 3),
                          ["Hand of Justice"], [], ["Carrot on a Stick"])
        self.assertEqual(d.kind, "reroll")

    def test_never_banish_spell(self):
        cards = self.offer(["Common", "Consecration"], ["Common", "Holy Light"], ["Common", "Exorcism"])
        d = select_action("level", cards, Controls("Reroll 2", "Skip +10 gold", ("Banish (3)",) * 3),
                          ["Hammer of Wrath"], [], ["Consecration"], min_rarity="Rare")
        self.assertEqual(d.kind, "reroll")

    def test_high_rarity_beats_adjacent_preference(self):
        cards = self.offer(["Rare", "Consecration"], ["Legendary", "Divine Shield"], ["Common", "Redemption"])
        d = select_action("level", cards, Controls(), ["Consecration", "Divine Shield"], [], [], min_rarity="Rare")
        self.assertEqual((d.kind, d.index), ("pick", 2))

    def test_priority_beats_lower_when_no_weight(self):
        cards = self.offer(["Rare", "Consecration"], ["Legendary", "Divine Shield"], ["Common", "Redemption"])
        d = select_action("level", cards, Controls(), ["Consecration", "Divine Shield"], [], [], min_rarity="Rare", rarity_weight=0)
        self.assertEqual((d.kind, d.index), ("pick", 1))

    def test_never_auto_spend_gold(self):
        cards = self.offer(["Uncommon", "A"], ["Uncommon", "B"], ["Rare", "C"])
        for text in ["Reroll 100 gold", "Reroll 5 coins", "Reroll 125 Gold R"]:
            d = select_action("level", cards, Controls(text, "Skip +10 gold"), ["Consecration"], [], [])
            self.assertEqual(d.kind, "skip", text)

    def test_unreadable_reroll_waits(self):
        cards = self.offer(["Uncommon", "A"], ["Uncommon", "B"], ["Rare", "C"])
        for text in ["Roll 4", "Reroll", "Reroll 100", "", "Reroll 14"]:
            d = select_action("level", cards, Controls(text, "Skip +10 gold"), ["Consecration"], [], [])
            self.assertEqual(d.kind, "wait", text)

    def test_unreadable_card_doesnt_waste_reroll_or_skip(self):
        cards = self.offer(["Rare", "Fireball"], ["Silver Ring"], ["Common", "Redemption"])
        d = select_action("loot", cards, Controls("Reroll 3", "Skip +10 gold"), ["Hand of Justice"], [], [])
        self.assertEqual(d.kind, "wait")

    def test_low_rarity_preferred_disallowed(self):
        cards = self.offer(["Common", "Consecration"], ["Common", "Redemption"], ["Common", "Exorcism"])
        d = select_action("level", cards, Controls("Reroll 2", "Skip +10 gold"), ["Consecration"], [], [], min_rarity="Epic")
        self.assertEqual(d.kind, "reroll")

    def test_avoid_prevents_selection(self):
        cards = self.offer(["Legendary", "Consecration"], ["Common", "Redemption"], ["Common", "Exorcism"])
        d = select_action("level", cards, Controls("Reroll 2", "Skip +10 gold"), ["Consecration"], ["Consecration"], [], min_rarity="Common")
        self.assertEqual(d.kind, "reroll")

    def test_reroll_parsing(self):
        self.assertEqual(parse_free_rerolls("Reroll 4"), 4)
        self.assertEqual(parse_free_rerolls("Reroll 0"), 0)
        self.assertEqual(parse_free_rerolls("Reroll 100 gold"), 0)
        self.assertIsNone(parse_free_rerolls("Reroll"))
        self.assertEqual(parse_banish_count("Banish (2)"), 2)
        self.assertEqual(parse_banish_count("Banish 0"), 0)

    def test_signature_changes_on_reroll_counter(self):
        cards = self.offer(["Common", "Consecration"], ["Common", "Holy Light"], ["Rare", "Exorcism"])
        a = action_fingerprint("level", cards, Controls("Reroll 4", "Skip +10 gold"))
        b = action_fingerprint("level", cards, Controls("Reroll 3", "Skip +10 gold"))
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()

from autopick.amulets import SPELL_AMULETS
from autopick.catalog import SPELLS, make_profiles, LEGENDARY_AMULETS
from autopick.advanced import choose, Policy, RunState
from autopick.strategy import parse_offers, Controls


def test_every_spell_is_accounted_for_in_spell_amulet_families():
    assert sum(map(len, SPELL_AMULETS.values())) == 104
    for klass, spells in SPELLS.items():
        assert set(SPELL_AMULETS[klass]) == set(spells)
    assert SPELL_AMULETS['Paladin']['Consecration'] == 'Amulet of the Inferno'
    assert SPELL_AMULETS['Mage']['Fireball'] == 'Eye of the Splitting Sky'
    assert SPELL_AMULETS['Shaman']['Lightning Shield'] is None


def test_ambiguous_named_legendary_no_longer_auto_equipped_without_spell_variant():
    profile=make_profiles()['Mage — Fire explosions']
    profile['loot']=['Eye of the Splitting Sky']
    cards=parse_offers([
        ['Legendary','Eye of the Splitting Sky'],
        ['Common','Royal Seal of Eldre\'Thalas'],
        ['Common','Carrot on a Stick'],
    ])
    a=choose('loot',cards,Controls('Reroll 100 gold','Skip +11 gold'),profile,
             Policy(min_loot_rarity='Rare',verify_legendary_variant=True),RunState())
    assert a.kind=='skip'


def test_legendary_can_be_recognised_when_visible_variant_is_correct():
    profile=make_profiles()['Mage — Fire explosions']
    profile['loot']=['Eye of the Splitting Sky']
    cards=parse_offers([
        ['Legendary','Eye of the Splitting Sky','Legendary amulet remakes Fireball'],
        ['Common','Royal Seal of Eldre\'Thalas'],
        ['Common','Carrot on a Stick'],
    ])
    a=choose('loot',cards,Controls('Reroll 100 gold','Skip +11 gold'),profile,
             Policy(min_loot_rarity='Rare',verify_legendary_variant=True),RunState())
    assert (a.kind,a.index,a.label)==('pick',1,'Eye of the Splitting Sky')

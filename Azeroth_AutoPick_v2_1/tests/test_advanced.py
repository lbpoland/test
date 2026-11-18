from autopick.advanced import (Policy, RunState, choose, make_passive_plan,
                              RARITY_MULTIPLIER, PASSIVES, ITEM_TYPE)
from autopick.catalog import make_profiles, SPELLS, RINGS, TRINKETS, AMULETS, LEGENDARY_AMULETS
from autopick.strategy import parse_offers, Controls, Action
from autopick.guides import enrich_profiles


def profile(klass='Paladin',style='Consecration AoE'):
    return make_profiles()[f'{klass} — {style}']


def cards(*data):
    return parse_offers(data)


def test_high_end_floor_does_not_choose_common_even_when_best_name():
    cs=cards(['Common','Consecration','Rank 7 » 8'],['Common','Redemption','New spell'],['Common','Exorcism','New spell'])
    a=choose('level',cs,Controls('Reroll 100 gold','Skip +11 gold'),profile(),Policy(min_spell_rarity='Rare',adaptive_rarity=False),RunState())
    assert a.kind=='skip'


def test_free_reroll_when_no_preferred_rare():
    cs=cards(['Uncommon','Hammer of Wrath'],['Common','Redemption'],['Common','Exorcism'])
    a=choose('level',cs,Controls('Reroll 4','Skip +11 gold'),profile(),Policy(min_spell_rarity='Rare'),RunState())
    assert a.kind=='reroll'


def test_best_rares_choose_priority_and_rank_up():
    cs=cards(['Rare','Consecration','Rank 7 » 8'],['Rare','Divine Shield','Rank 1 » 2'],['Common','Redemption'])
    a=choose('level',cs,Controls('Reroll 3','Skip +11 gold'),profile(),Policy(min_spell_rarity='Rare'),RunState())
    assert (a.kind,a.index,a.label)==('pick',1,'Consecration')


def test_four_card_opening_hand():
    cs=cards(['Common','Redemption'],['Common','Holy Light'],['Rare','Consecration'],['Rare','Holy Shield'])
    a=choose('level',cs,Controls('Reroll 3','Skip +11 gold'),profile(),Policy(),RunState())
    assert (a.kind,a.index)==('pick',3)


def test_passive_suggestion_only_if_visible():
    cs=cards(['Rare','Power Word: Fortitude'],['Uncommon','Redemption'],['Common','Holy Light'])
    a=choose('level',cs,Controls('Reroll 2','Skip +11 gold'),profile(),Policy(),RunState())
    assert a.kind=='pick' and a.label=='Power Word: Fortitude'


def test_prevent_amulet_swap_and_allow_own_upgrade():
    state=RunState(equipped_amulet='Malice Stone Pendant')
    cs=cards(['Legendary','Choker of the Fire Lord'],['Rare','Archimtiros\' Ring of Reckoning'],['Epic','Malice Stone Pendant'])
    p=profile('Mage','Arcane echo')
    p['loot']=['Choker of the Fire Lord','Malice Stone Pendant']
    assert choose('loot',cs,Controls(),p,Policy(min_loot_rarity='Rare',protect_amulet=True),state).label=='Malice Stone Pendant'
    assert choose('loot',cs,Controls(),p,Policy(min_loot_rarity='Rare',protect_amulet=False),state).kind=='pick'


def test_protect_both_ring_slots():
    state=RunState(equipped_rings=['Band of Accuria','Quick Strike Ring'])
    p=profile();p['loot']=['Ring of Spell Power','Hand of Justice']
    cs=cards(['Legendary','Ring of Spell Power'],['Epic','Hand of Justice'],['Common','Carrot on a Stick'])
    a=choose('loot',cs,Controls(),p,Policy(protect_jewelry=True),state)
    assert a.kind=='pick' and a.label=='Hand of Justice'


def test_banish_explicit_jewellery_when_no_good_offers():
    p=profile();p['banish_loot']=['Carrot on a Stick']
    cs=cards(['Common','Carrot on a Stick'],['Common','Onyxia Blood Talisman'],['Common','Insignia of the Horde'])
    a=choose('loot',cs,Controls('Reroll 3','Skip +11 gold',('Banish (2)',)*3),p,Policy(),RunState())
    assert a.kind=='banish' and a.label=='Carrot on a Stick'


def test_never_banish_when_good_pick_exists():
    p=profile();p['banish_loot']=['Carrot on a Stick']
    cs=cards(['Common','Carrot on a Stick'],['Epic','Quick Strike Ring'],['Common','Insignia of the Horde'])
    a=choose('loot',cs,Controls('Reroll 3','Skip +11 gold',('Banish (2)',)*3),p,Policy(),RunState())
    assert a.kind=='pick'


def test_never_re_banish_same_name_during_run():
    p=profile();p['banish_loot']=['Carrot on a Stick']
    cs=cards(['Common','Carrot on a Stick'],['Common','Onyxia Blood Talisman'],['Common','Insignia of the Horde'])
    run=RunState(used_banish={'carrot on a stick'})
    a=choose('loot',cs,Controls('Reroll 2','Skip +11 gold',('Banish (2)',)*3),p,Policy(),run)
    assert a.kind=='reroll'


def test_never_banish_over_limit():
    p=profile();p['banish_loot']=['Carrot on a Stick']
    cs=cards(['Common','Carrot on a Stick'],['Common','Onyxia Blood Talisman'],['Common','Insignia of the Horde'])
    a=choose('loot',cs,Controls('Reroll 2','Skip +11 gold',('Banish (2)',)*3),p,Policy(max_banish_per_run=1),RunState(banishes=1))
    assert a.kind=='reroll'


def test_reroll_free_reservation_skips_unwanted_offer():
    cs=cards(['Common','Hammer of Wrath'],['Common','Redemption'],['Common','Exorcism'])
    a=choose('level',cs,Controls('Reroll 2','Skip +11 gold'),profile(),Policy(max_rerolls_reserved=2),RunState())
    assert a.kind=='skip'


def test_reroll_ambiguous_never_guess():
    cs=cards(['Common','Hammer of Wrath'],['Common','Redemption'],['Common','Exorcism'])
    for txt in ('Reroll 100','Reroll','', 'Reroll fourteen'):
        assert choose('level',cs,Controls(txt,'Skip +11 gold'),profile(),Policy(),RunState()).kind=='wait'


def test_runstate_remembers_jewellery_and_spells():
    run=RunState()
    run.remember(Action('pick',label='Consecration'),'level','Paladin')
    run.remember(Action('pick',label='Quick Strike Ring'),'loot','Paladin')
    run.remember(Action('pick',label='Malice Stone Pendant'),'loot','Paladin')
    run.remember(Action('banish',label='Carrot on a Stick'),'loot','Paladin')
    assert run.known_spells['Consecration']==1
    assert run.equipped_rings==['Quick Strike Ring']
    assert run.equipped_amulet=='Malice Stone Pendant'
    assert run.banishes==1 and 'carrot on a stick' in run.used_banish
    run.reset()
    assert not run.known_spells and run.banishes==0


def test_jewelry_catalogue_has_all_groups_and_recommendation_metadata():
    assert len(RINGS)==9 and len(TRINKETS)==14
    assert len(AMULETS)==20 and len(LEGENDARY_AMULETS)==15
    assert len(ITEM_TYPE)==58
    assert RARITY_MULTIPLIER['Legendary']==3.2
    assert len(PASSIVES)==10
    assert len(SPELLS)==9


def test_27_presets_have_guides_and_6_spell_plans():
    plans=enrich_profiles(make_profiles())
    assert len(plans)==27
    for p in plans.values():
        assert len(p['level'])==6
        assert p['capstone'] and p['race'] and p['description']
        assert len(make_passive_plan(p['style'],p['class']))==6

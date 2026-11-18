"""Class-spell to named legendary amulet-family mappings.

These names represent the family of a legendary spell modifier; a single
amulet family may target many different spells. When the card does not reveal
which spell it remakes, the selection engine must not guess the variant.
Data is based on ASBuilder Data.lua (1 November 2026 source snapshot).
"""
from .catalog import SPELLS

NONE='—'
FAMILY={
'Warrior': 'Medallion of the Bladestorm|Heart of the Earthshaker|Heart of the Earthshaker|Medallion of the Bladestorm|The Reaper\'s Amulet|Heart of the Earthshaker|The Eternal Talisman|Medallion of the Bladestorm|Pendant of the Plague|Medallion of the Bladestorm|Charm of the Fated Hour',
'Paladin': 'Amulet of the Inferno|Eye of the Splitting Sky|Eye of the Splitting Sky|Stormcaller\'s Amulet|Heart of the Earthshaker|Eye of the Splitting Sky|Eye of the Splitting Sky|The Eternal Talisman|The Eternal Talisman|The Eternal Talisman|Charm of the Fated Hour',
'Hunter': 'Eye of the Splitting Sky|Eye of the Splitting Sky|Eye of the Splitting Sky|Pendant of the Plague|Amulet of the Inferno|Heart of the Earthshaker|Eye of the Splitting Sky|Eye of the Splitting Sky|Amulet of the Inferno|Amulet of the Inferno|Charm of the Fated Hour',
'Rogue': 'Medallion of the Bladestorm|The Reaper\'s Amulet|Heart of the Earthshaker|Pendant of the Plague|Medallion of the Bladestorm|Medallion of the Bladestorm|Medallion of the Bladestorm|The Eternal Talisman|The Reaper\'s Amulet|The Eternal Talisman|Charm of the Fated Hour',
'Priest': 'Eye of the Splitting Sky|Pendant of the Plague|Eye of the Splitting Sky|Heart of the Earthshaker|The Eternal Talisman|The Eternal Talisman|Eye of the Splitting Sky|Breath of the Black Dragon|Heart of the Earthshaker|Pendant of the Plague|Charm of the Fated Hour',
'Shaman': 'Eye of the Splitting Sky|Talisman of the Tempest|Earthshatter Seal|Emberwake Pendant|Winter\'s Embrace|—|Amulet of the Ancients|Amulet of the Ancients|Cinderheart Pendant|—|Eye of the Tempest|Heart of the Earthbreaker',
'Mage': 'Eye of the Splitting Sky|Eye of the Splitting Sky|Stormcaller\'s Amulet|Heart of the Earthshaker|Heart of the Earthshaker|Amulet of the Inferno|Amulet of the Inferno|Stormcaller\'s Amulet|Breath of the Black Dragon|Heart of the Earthshaker|Eye of the Splitting Sky|The Eternal Talisman|Charm of the Fated Hour',
'Warlock': 'Eye of the Splitting Sky|Pendant of the Plague|Pendant of the Plague|Pendant of the Plague|Amulet of the Inferno|Heart of the Earthshaker|Eye of the Splitting Sky|Stormcaller\'s Amulet|Pendant of the Plague|Eye of the Splitting Sky|Charm of the Fated Hour|The Legionlord\'s Medallion',
'Druid': 'Eye of the Splitting Sky|Pendant of the Plague|Eye of the Splitting Sky|Amulet of the Inferno|Pendant of the Plague|Eye of the Splitting Sky|The Eternal Talisman|The Eternal Talisman|The Eternal Talisman|Heart of the Earthshaker|Charm of the Fated Hour|Medallion of the Bladestorm',
}
SPELL_AMULETS={}
for klass,group in FAMILY.items():
    family=group.split('|')
    assert len(family)==len(SPELLS[klass]),(klass,len(family),len(SPELLS[klass]))
    SPELL_AMULETS[klass]={spell: (None if target==NONE else target)
                          for spell,target in zip(SPELLS[klass],family)}


def available_spell_amulets(klass:str,owned_spells:set[str])->list[tuple[str,str]]:
    """Variants potentially eligible from the observed/inferred known spells."""
    return [(spell,amulet) for spell,amulet in SPELL_AMULETS.get(klass,{}).items()
            if spell in owned_spells and amulet]

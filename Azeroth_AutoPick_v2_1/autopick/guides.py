"""Build guide notes / advisory capstones (not live talent automation).

Primary source: azerothsurvivorsgame.com/builds, checked 2026-11-03 for
0.139.0. Capstones are game talent names; pairing to this app's personal
styles is editorial, and can be adjusted in individual profiles.
"""
CAPSTONES={
 'Warrior': ['Bladestorm','Titan','Mortal Wounds'],
 'Paladin': ["Light's Grace",'Hammer of the Righteous','Divine Storm'],
 'Hunter': ['Kill Shot','Bestial Wrath','Wyvern Sting'],
 'Rogue': ['Killing Spree','Shadow Dance','Toxic Bloom'],
 'Priest': ['Chastise','Shadowform','Penance'],
 'Shaman': ['Elemental Mastery','Totemic Wrath','Stormbound Echoes'],
 'Mage': ['Pyroclasm','Arcane Power','Summon Water Elemental'],
 'Warlock': ['Seed of Corruption','Pact of the Nathrezim','Rain of Chaos'],
 'Druid': ['Force of Nature','Dire Bear Form','Tree of Life'],
}
RACES={
 'Warrior':'Orc or Tauren', 'Paladin':'Dwarf or Human',
 'Hunter':'Troll', 'Rogue':'Night Elf', 'Priest':'Undead or Dwarf',
 'Shaman':'Troll or Orc', 'Mage':'Gnome', 'Warlock':'Gnome or Orc',
 'Druid':'Night Elf or Tauren'
}
BUILD_NOTES={
 'Warrior':['Repeated area Whirlwind and haste','Mitigation and maximum-health scaling','Bleeds plus resets on executes'],
 'Paladin':['Consecration uptime, area and survival','Shield synergies and high max health','Exorcism chains and critical strikes'],
 'Hunter':['Aimed Shot resets and crit chance','Wide area and shot coverage','Crowd-control traps and mobility'],
 'Rogue':['Fast chained attacks and cleaves','Single-target crit burst and executes','Bleeds and close-range sustain'],
 'Priest':['Holy Nova, shield break and crit procs','Shadow pain spread and DoT haste','Shield, healing and free holy spells'],
 'Shaman':['Chain Lightning, jumps and haste','Totem uptime and free fire nova','Shock control; capstone depends on talents'],
 'Mage':['Fire crits, Ignite and explosion chains','Echo chains and rapid arcane casts','Splintering frost and freezing control'],
 'Warlock':['DoT spread, procs and life drain','Voidwalker shields and defensive scaling','Rain of Fire and burning area damage'],
 'Druid':['Moonfire + Starfire procs + treants','Bear health/armor and regenerating attacks','Nature DoTs and self-healing'],
}

def enrich_profiles(profiles:dict):
    """Add documentation to the preset profiles without replacing user edits."""
    from .catalog import BUILD_PLANS
    for klass,styles in BUILD_PLANS.items():
        for idx,style in enumerate(styles):
            key=f'{klass} — {style}'
            if key not in profiles:continue
            p=profiles[key]
            p.setdefault('capstone',CAPSTONES[klass][idx])
            p.setdefault('race',RACES[klass])
            p.setdefault('description',BUILD_NOTES[klass][idx])
            p.setdefault('verified_capstone',False)
    return profiles

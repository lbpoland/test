"""Community-sourced catalogue snapshot, 2026-11-03. Spell names / jewellery are
from ASBuilder Data.lua (2026-11-01), not a runtime API or authoritative balance sim.
Strategies are editable heuristics, not optimality guarantees.
"""
SPELLS = {
'Warrior': 'Cleave|Whirlwind|Thunder Clap|Mortal Strike|Execute|Demoralizing Shout|Battle Shout|Bloodthirst|Rend|Shield Slam|Bloodrage',
'Paladin': 'Consecration|Exorcism|Hammer of Wrath|Holy Shock|Holy Wrath|Judgement|Hammer of Justice|Holy Light|Divine Shield|Holy Shield|Redemption',
'Hunter': 'Auto Shot|Arcane Shot|Multi-Shot|Serpent Sting|Volley|Explosive Trap|Concussive Shot|Aimed Shot|Immolation Trap|Frost Trap|Hunter\'s Mark',
'Rogue': 'Sinister Strike|Eviscerate|Blade Flurry|Rupture|Kidney Shot|Gouge|Ghostly Strike|Adrenaline Rush|Backstab|Slice and Dice|Seal Fate',
'Priest': 'Smite|Shadow Word: Pain|Mind Blast|Holy Nova|Power Word: Shield|Renew|Holy Fire|Mind Flay|Psychic Scream|Devouring Plague|Lightwell',
'Shaman': 'Lightning Bolt|Chain Lightning|Earth Shock|Flame Shock|Frost Shock|Lightning Shield|Magma Totem|Searing Totem|Fire Nova|Healing Wave|Stormstrike|Rockbiter Weapon',
'Mage': 'Fireball|Frostbolt|Arcane Missiles|Frost Nova|Arcane Explosion|Blizzard|Flamestrike|Fire Blast|Cone of Cold|Blast Wave|Pyroblast|Ice Barrier|Polymorph',
'Warlock': 'Shadow Bolt|Corruption|Immolate|Curse of Agony|Rain of Fire|Hellfire|Death Coil|Searing Pain|Drain Life|Fear|Soulfire|Demonic Empowerment',
'Druid': 'Wrath|Moonfire|Starfire|Hurricane|Insect Swarm|Entangling Roots|Rejuvenation|Regrowth|Thorns|Swipe|Faerie Fire|Shred',
}
SPELLS = {k: v.split('|') for k,v in SPELLS.items()}
RINGS = 'Band of Accuria|Quick Strike Ring|Heavy Dark Iron Ring|Master Dragonslayer\'s Ring|Archimtiros\' Ring of Reckoning|Ring of the Devoured|Ring of Spell Power|Seal of the Damned|Blooddrinker\'s Band'.split('|')
TRINKETS = 'Earthstrike|Talisman of Ephemeral Power|Lifegiving Gem|Hand of Justice|Blackhand\'s Breadth|Carrot on a Stick|Gnomish Universal Remote|Insignia of the Horde|Royal Seal of Eldre\'Thalas|Mark of the Chosen|Onyxia Blood Talisman|Horn of the Warchief|Major Soulstone|Star of Mystaria'.split('|')
AMULETS = 'Mark of Fordring|Talvash\'s Enhancing Necklace|Pristine Enchanted South Seas Kelp|Prestor\'s Talisman of Connivery|Animated Chain Necklace|Woven Ivy Necklace|Amulet of the Darkmoon|Jeklik\'s Opaline Talisman|The Eye of Hakkar|Medallion of Steadfast Might|Choker of Enlightenment|Amulet of Vek\'nilash|Pendant of the Fallen Dragon|Malice Stone Pendant|Onyxia Tooth Pendant|Choker of the Fire Lord'.split('|')
LEGENDARY_AMULETS = 'Eye of the Splitting Sky|Stormcaller\'s Amulet|Heart of the Earthshaker|Amulet of the Inferno|Talisman of the Tempest|Medallion of the Bladestorm|Pendant of the Plague|The Reaper\'s Amulet|Breath of the Black Dragon|The Eternal Talisman|Amulet of the Ancients|Charm of the Fated Hour|The Legionlord\'s Medallion|Eye of the Tempest|Cinderheart Pendant|Winter\'s Embrace|Earthshatter Seal|Emberwake Pendant|Heart of the Earthbreaker'.split('|')
# Four spell-agnostic amulets appeared in the shared Codex list in v0.139;
# older ASBuilder snapshots placed their names among the legendary families.
EXTRA_SHARED = ["Cinderheart Pendant", "Winter's Embrace", "Earthshatter Seal", "Emberwake Pendant"]
AMULETS = AMULETS + EXTRA_SHARED
LEGENDARY_AMULETS = [x for x in LEGENDARY_AMULETS if x not in EXTRA_SHARED]
JEWELRY = RINGS + TRINKETS + AMULETS + LEGENDARY_AMULETS
# These are policy archetypes and personalisable starting points, not measured DPS rankings.
BUILD_PLANS = {
'Warrior': {
 'Whirlwind AoE': ['Whirlwind','Thunder Clap','Battle Shout','Bloodthirst','Mortal Strike','Execute'],
 'Shield survival': ['Shield Slam','Demoralizing Shout','Battle Shout','Whirlwind','Bloodthirst','Thunder Clap'],
 'Bleed / execute': ['Rend','Execute','Mortal Strike','Bloodthirst','Whirlwind','Battle Shout']},
'Paladin': {
 'Consecration AoE': ['Consecration','Holy Shield','Divine Shield','Holy Wrath','Holy Light','Judgement'],
 'Shield bastion': ['Divine Shield','Holy Shield','Consecration','Holy Light','Hammer of Justice','Holy Wrath'],
 'Holy burst': ['Holy Shock','Exorcism','Hammer of Wrath','Holy Wrath','Consecration','Judgement']},
'Hunter': {
 'Crit sniper': ['Aimed Shot','Auto Shot','Arcane Shot','Multi-Shot','Hunter\'s Mark','Concussive Shot'],
 'Volley AoE': ['Volley','Multi-Shot','Explosive Trap','Arcane Shot','Auto Shot','Frost Trap'],
 'Trap control': ['Explosive Trap','Immolation Trap','Frost Trap','Volley','Multi-Shot','Concussive Shot']},
'Rogue': {
 'Blade Flurry': ['Blade Flurry','Slice and Dice','Sinister Strike','Adrenaline Rush','Eviscerate','Kidney Shot'],
 'Crit assassin': ['Eviscerate','Backstab','Sinister Strike','Seal Fate','Adrenaline Rush','Ghostly Strike'],
 'Bleed sustain': ['Rupture','Slice and Dice','Blade Flurry','Sinister Strike','Eviscerate','Gouge']},
'Priest': {
 'Holy Nova AoE': ['Holy Nova','Power Word: Shield','Renew','Holy Fire','Smite','Psychic Scream'],
 'Shadow DoT': ['Shadow Word: Pain','Devouring Plague','Mind Flay','Mind Blast','Power Word: Shield','Holy Nova'],
 'Defensive holy': ['Power Word: Shield','Renew','Holy Nova','Lightwell','Holy Fire','Smite']},
'Shaman': {
 'Chain lightning': ['Chain Lightning','Lightning Bolt','Lightning Shield','Earth Shock','Fire Nova','Magma Totem'],
 'Totem AoE': ['Magma Totem','Fire Nova','Searing Totem','Chain Lightning','Lightning Shield','Healing Wave'],
 'Elemental control': ['Earth Shock','Frost Shock','Flame Shock','Chain Lightning','Lightning Shield','Healing Wave']},
'Mage': {
 'Fire explosions': ['Fireball','Pyroblast','Flamestrike','Fire Blast','Blast Wave','Ice Barrier'],
 'Arcane echo': ['Arcane Missiles','Arcane Explosion','Ice Barrier','Frost Nova','Blizzard','Fireball'],
 'Frost control': ['Frostbolt','Blizzard','Frost Nova','Cone of Cold','Ice Barrier','Arcane Explosion']},
'Warlock': {
 'DoT spread': ['Corruption','Curse of Agony','Immolate','Rain of Fire','Drain Life','Death Coil'],
 'Voidwalker sustain': ['Demonic Empowerment','Drain Life','Death Coil','Corruption','Shadow Bolt','Rain of Fire'],
 'Fire AoE': ['Rain of Fire','Hellfire','Immolate','Searing Pain','Drain Life','Death Coil']},
'Druid': {
 'Starfall caster': ['Starfire','Moonfire','Wrath','Hurricane','Rejuvenation','Entangling Roots'],
 'Bear survival': ['Swipe','Thorns','Regrowth','Rejuvenation','Insect Swarm','Entangling Roots'],
 'Nature DoT': ['Insect Swarm','Moonfire','Hurricane','Wrath','Rejuvenation','Entangling Roots']},
}
JEWELRY_PLANS = {
 'aoe': ['Quick Strike Ring','Ring of Spell Power','Talisman of Ephemeral Power','Hand of Justice','Band of Accuria','Star of Mystaria','Malice Stone Pendant','Choker of the Fire Lord'],
 'crit': ['Master Dragonslayer\'s Ring','Blackhand\'s Breadth','Band of Accuria','Hand of Justice','Earthstrike','Quick Strike Ring','Onyxia Tooth Pendant'],
 'tank': ['Archimtiros\' Ring of Reckoning','Star of Mystaria','Heavy Dark Iron Ring','Lifegiving Gem','Blooddrinker\'s Band','Quick Strike Ring','Onyxia Blood Talisman'],
 'dot': ['Seal of the Damned','Quick Strike Ring','Earthstrike','Band of Accuria','Blooddrinker\'s Band','Pendant of the Plague','Hand of Justice'],
 'echo': ['Hand of Justice','Malice Stone Pendant','Quick Strike Ring','Talisman of Ephemeral Power','Band of Accuria','Earthstrike'],
 'speed': ['Quick Strike Ring','Talisman of Ephemeral Power','Band of Accuria','Hand of Justice','Ring of Spell Power','Earthstrike'],
}
PLAN_JEWELRY = {
 'Warrior': ['aoe','tank','dot'], 'Paladin':['aoe','tank','crit'],
 'Hunter':['crit','aoe','tank'], 'Rogue':['speed','crit','dot'],
 'Priest':['aoe','dot','tank'], 'Shaman':['aoe','aoe','tank'],
 'Mage':['aoe','echo','tank'], 'Warlock':['dot','tank','aoe'],
 'Druid':['aoe','tank','dot']}

def make_profiles():
    data={}
    for cls, builds in BUILD_PLANS.items():
        for i,(style, spells) in enumerate(builds.items()):
            assert len(set(spells)) == len(spells)
            assert set(spells).issubset(SPELLS[cls]), (cls, style)
            data[f'{cls} — {style}'] = {
                'class': cls, 'style': style, 'level': spells,
                'loot': JEWELRY_PLANS[PLAN_JEWELRY[cls][i]],
                'avoid': [], 'banish_loot': [],
                'policy': {'level_min':'Common','loot_min':'Rare', 'new_spell_min':'Common',
                           'upgrade_min':'Common', 'prefer_upgrades':False,
                           'fill_slots_first':True,'allow_free_rerolls':True,'allow_gold_rerolls':False,
                           'max_auto_banish_per_run':0}
            }
    return data

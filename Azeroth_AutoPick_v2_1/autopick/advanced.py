"""Advanced, auditable, game-screen-only decision engine.

This module does not pretend to know random outcomes or hidden game state.
One decision is a function of visible offered cards, visible button text,
an editable profile, and a conservatively tracked run history.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
from .strategy import (Action, Controls, OfferedCard, RARITIES, RARITY_RANK,
                       parse_free_rerolls, parse_banish_count, skip_is_available,
                       best_named_match, is_avoided)
from .engine import clean, match_quality
from .catalog import RINGS, TRINKETS, AMULETS, LEGENDARY_AMULETS, SPELLS
from .amulets import SPELL_AMULETS

# Advisory passive names are from the community rebuild. The original game's
# live passive spell labels are not guaranteed identical. Matching is exact-ish
# and automatic selection happens only if those names are actually visible.
PASSIVES = {
    'Blessing of Might': ('damage','offense'),
    'Arcane Intellect': ('haste','offense'),
    'Amplify Magic': ('area','offense'),
    'Blessing of Kings': ('crit','offense'),
    'Power Word: Fortitude': ('health','survival'),
    'Renew': ('regen','survival'),
    'Mark of the Wild': ('armor','survival'),
    'Aspect of the Pack': ('speed','utility'),
    'Detect Lesser Invisibility': ('pickup','utility'),
    'Blessing of Wisdom': ('experience','utility'),
}

ITEM_TAGS = {
    'Band of Accuria':('damage',), 'Quick Strike Ring':('haste',),
    'Heavy Dark Iron Ring':('health',), "Master Dragonslayer's Ring":('crit',),
    "Archimtiros' Ring of Reckoning":('health','armor'),
    'Ring of the Devoured':('regen',), 'Ring of Spell Power':('area',),
    'Seal of the Damned':('dot',), "Blooddrinker's Band":('leech','survival'),
    'Earthstrike':('damage',),'Talisman of Ephemeral Power':('haste',),
    'Lifegiving Gem':('health',), 'Hand of Justice':('echo',),
    "Blackhand's Breadth":('crit',),'Carrot on a Stick':('speed',),
    'Gnomish Universal Remote':('pickup',),'Insignia of the Horde':('experience',),
    "Royal Seal of Eldre'Thalas":('gold',), 'Mark of the Chosen':('luck',),
    'Onyxia Blood Talisman':('heal',), 'Horn of the Warchief':('buff',),
    'Major Soulstone':('survival',), 'Star of Mystaria':('health','armor'),
    'Mark of Fordring':('damage',), "Talvash's Enhancing Necklace":('haste',),
    'Pristine Enchanted South Seas Kelp':('luck','gold'),
    "Prestor's Talisman of Connivery":('crit','damage'),
    'Animated Chain Necklace':('health',), 'Woven Ivy Necklace':('regen','speed'),
    'Amulet of the Darkmoon':('haste','speed'),
    "Jeklik's Opaline Talisman":('regen',),
    'The Eye of Hakkar':('crit','dot'),
    'Medallion of Steadfast Might':('survival','thorns'),
    'Choker of Enlightenment':('chain','area'),
    "Amulet of Vek'nilash":('targets','damage'),
    'Pendant of the Fallen Dragon':('survival','regen'),
    'Malice Stone Pendant':('echo','haste'),
    'Onyxia Tooth Pendant':('crit','area'),
    'Choker of the Fire Lord':('aoe','damage'),
}
ITEM_TYPE = {clean(x):kind for kind, names in (
    ('ring',RINGS),('trinket',TRINKETS),('amulet', AMULETS + LEGENDARY_AMULETS))
    for x in names}
# Some names (Renew, etc.) occur in different contexts; only consider them
# passives when class spells do not have the same name.
SPELL_MEMBERSHIP = {clean(v):set() for names in SPELLS.values() for v in names}
for k,names in SPELLS.items():
    for n in names: SPELL_MEMBERSHIP[clean(n)].add(k)

RARITY_MULTIPLIER = {'Common':1.0,'Uncommon':1.4,'Rare':1.8,'Epic':2.4,'Legendary':3.2}

@dataclass
class RunState:
    """A best-effort *inferred* inventory, from actions issued by this app.

    It is not a read of server state. It can become stale if the player manually
    takes cards; reset it on each new run and show the caveat in the GUI.
    """
    known_spells: dict[str,int] = field(default_factory=dict)
    known_passives: dict[str,int] = field(default_factory=dict)
    equipped_rings: list[str] = field(default_factory=list)
    equipped_trinkets: list[str] = field(default_factory=list)
    equipped_amulet: str = ''
    used_banish: set[str] = field(default_factory=set)
    level_seen: int = 0
    picks: int = 0
    rerolls: int = 0
    skips: int = 0
    banishes: int = 0
    last_reroll_free: int|None = None
    def reset(self):
        self.__dict__.update(RunState().__dict__)
    def remember(self, action:Action, kind:str, klass:str=''):
        if action.kind=='reroll': self.rerolls+=1
        if action.kind=='skip': self.skips+=1
        if action.kind=='banish':
            self.banishes+=1; self.used_banish.add(clean(action.label))
        if action.kind!='pick': return
        self.picks+=1
        name=action.label
        if kind=='level':
            store = self.known_passives if clean(name) in (clean(p) for p in PASSIVES) and clean(name) not in {clean(n) for n in SPELLS.get(klass,[])} else self.known_spells
            store[name]=store.get(name,0)+1
        elif kind=='loot':
            slot=ITEM_TYPE.get(clean(name))
            if slot in ('ring','trinket'):
                arr=self.equipped_rings if slot=='ring' else self.equipped_trinkets
                if name not in arr:
                    if len(arr)>=2: arr.pop(0)
                    arr.append(name)
            elif slot=='amulet':
                self.equipped_amulet=name
    def as_dict(self):
        return {'spells':dict(self.known_spells),'passives':dict(self.known_passives),
                'rings':list(self.equipped_rings),'trinkets':list(self.equipped_trinkets),
                'amulet':self.equipped_amulet,'picks':self.picks,'rerolls':self.rerolls,
                'skips':self.skips,'banishes':self.banishes}

@dataclass(frozen=True)
class Policy:
    min_spell_rarity: str='Uncommon'
    min_loot_rarity: str='Rare'
    min_new_rarity: str='Uncommon'
    min_upgrade_rarity: str='Common'
    adaptive_rarity: bool=False
    prefer_core_upgrades: bool=True
    max_rerolls_reserved: int=0
    auto_banish: bool=True
    max_banish_per_run: int=2
    auto_skip: bool=True
    auto_free_reroll: bool=True
    protect_amulet: bool=True
    protect_jewelry: bool=True
    accept_passives: bool=True
    min_confidence: float=.88
    rarity_weight: float=1.0
    health_emergency: bool=False
    verify_legendary_variant: bool=True
    @classmethod
    def from_dict(cls, settings:dict):
        import dataclasses
        fields={x.name for x in dataclasses.fields(cls)}
        return cls(**{k:v for k,v in settings.items() if k in fields})


def _effective_floor(kind, card, policy, run:RunState, free:int|None):
    base=policy.min_spell_rarity if kind=='level' else policy.min_loot_rarity
    if kind=='level':
        specific=policy.min_upgrade_rarity if card.upgrade else policy.min_new_rarity
        # Strict combined floor, unless user explicitly chooses relaxed upgrading.
        if RARITY_RANK.get(clean(specific),0)>RARITY_RANK.get(clean(base),0): base=specific
    if policy.adaptive_rarity and kind=='level' and free==0 and card.upgrade:
        # When no free rerolls remain, an improvement to a core spell can be
        # useful instead of repeated skips; honours the explicit upgrade floor.
        base=policy.min_upgrade_rarity
    return RARITY_RANK.get(clean(base), 99)


def _guess_card_name(card:OfferedCard, choices:Sequence[str], confidence:float):
    """Find a single high-quality exact/cautious fuzzy match to visible title."""
    matches=[]
    for name in choices:
        q=match_quality(name,card.lines)
        if q>=confidence:
            matches.append((q,name))
    if not matches: return None
    matches.sort(key=lambda pair:(pair[0], len(pair[1])),reverse=True)
    # Ambiguous OCR matches should not trigger an irreversible decision.
    if len(matches)>1 and matches[0][0]<.999 and matches[0][0]-matches[1][0]<.025:
        return None
    return matches[0][1],matches[0][0]


def make_passive_plan(style:str,klass:str)->list[str]:
    s=clean(style)
    if any(x in s for x in ('shield','bear','survival','sustain','defensive','tank')):
        return ['Power Word: Fortitude','Mark of the Wild','Blessing of Might','Arcane Intellect','Blessing of Kings','Amplify Magic']
    if any(x in s for x in ('crit','sniper','assassin','holy burst')):
        return ['Blessing of Kings','Blessing of Might','Arcane Intellect','Amplify Magic','Power Word: Fortitude','Aspect of the Pack']
    if any(x in s for x in ('arcane','echo','speed','lightning','flurry')):
        return ['Arcane Intellect','Blessing of Might','Amplify Magic','Blessing of Kings','Power Word: Fortitude','Mark of the Wild']
    return ['Blessing of Might','Arcane Intellect','Amplify Magic','Power Word: Fortitude','Blessing of Kings','Mark of the Wild']


def synergy_tags(profile:dict)->set[str]:
    text=clean(profile.get('style','')+' '+' '.join(profile.get('level',[])[:3]))
    tags={'damage'}
    if any(x in text for x in ('area','explosion','nova','whirlwind','blizzard','aoe','storm','fire')):
        tags|={'area','aoe','haste','echo','targets'}
    if any(x in text for x in ('shield','surviv','bear','sustain')):
        tags|={'health','armor','regen','leech','survival','buff'}
    if any(x in text for x in ('crit','sniper','assassin','pyroblast','holy burst')):
        tags|={'crit','echo','damage'}
    if any(x in text for x in ('dot','plague','bleed')): tags|={'dot','haste','leech'}
    if 'warlock' in clean(profile.get('class','')): tags.add('survival')
    return tags


def choose(kind:str, cards:Sequence[OfferedCard], controls:Controls,
           profile:dict, policy:Policy, run:RunState) -> Action:
    """Score only visible, positively recognised offers. Never spend gold.

    The method is not a learned or mathematically optimal model. More advanced
    game physics, unpublished rates, talent trees and gear are not available via
    the documented addon API. This explicitly encodes risk preferences.
    """
    if kind not in ('level','loot') or len(cards) not in (3,4) or len(set(c.index for c in cards))!=len(cards):
        return Action('wait',reason='Unknown card layout')
    if any(not c.lines or c.rarity not in RARITIES for c in cards):
        return Action('wait',reason='Incomplete card text or rarity')
    rerolls=parse_free_rerolls(controls.reroll_text)
    klass=profile.get('class','')
    spellpool=SPELLS.get(klass,[])
    passive_plan=profile.get('passives') or make_passive_plan(profile.get('style',''),klass)
    priorities=profile.get('level',[]) if kind=='level' else profile.get('loot',[])
    avoid=profile.get('avoid',[])
    blocked_names=profile.get('banish_loot',[])
    tags=synergy_tags(profile)
    eligible=[]
    for c in cards:
        if is_avoided(c,avoid,policy.min_confidence): continue
        floor=_effective_floor(kind,c,policy,run,rerolls)
        if RARITY_RANK[c.rarity.lower()]<floor: continue
        offered=_guess_card_name(c,priorities,policy.min_confidence)
        passive=False
        if kind=='level' and policy.accept_passives:
            match_passive=_guess_card_name(c,passive_plan,policy.min_confidence)
            if match_passive and (not offered or match_passive[1]>offered[1]):
                offered=match_passive;passive=True
        if not offered: continue
        label,quality=offered
        # If it's a rank 8 spell or rank 5 passive already, do not choose.
        if c.upgrade and any('rank 8' in clean(row) and '8 8' in clean(row) for row in c.lines):continue
        if kind=='loot':
            kind_of_item=ITEM_TYPE.get(clean(label))
            if not kind_of_item: continue
            if kind_of_item=='amulet' and label in LEGENDARY_AMULETS and policy.verify_legendary_variant:
                # One named family may describe several different spell-specific
                # legendary effects. The title alone cannot establish the variant.
                # Require visible text to say which *planned* spell it remakes.
                matching_spell = [spell for spell, family in SPELL_AMULETS.get(klass,{}).items()
                                  if family==label and spell in profile.get('level',[])]
                if not any(('remake' in clean(line) or 'spell' in clean(line)) and
                           any(clean(spell) in clean(line) for spell in matching_spell)
                           for line in c.lines):
                    continue
            if kind_of_item=='amulet' and policy.protect_amulet and run.equipped_amulet and clean(label)!=clean(run.equipped_amulet):
                continue
            if kind_of_item=='ring' and policy.protect_jewelry and len(run.equipped_rings)>=2 and label not in run.equipped_rings:
                continue
            if kind_of_item=='trinket' and policy.protect_jewelry and len(run.equipped_trinkets)>=2 and label not in run.equipped_trinkets:
                continue
        # A good build spell takes priority over filler passives early.
        seq=passive_plan if passive else priorities
        prio=seq.index(label) if label in seq else 99
        rarity_scale=RARITY_MULTIPLIER[c.rarity]
        score=200 - prio*15 + (rarity_scale-1)*43*policy.rarity_weight
        if c.upgrade and policy.prefer_core_upgrades: score+=12
        if kind=='level' and c.upgrade and prio<3:score+=15
        if passive: score-=9
        if kind=='level' and not c.upgrade and not passive and len(run.known_spells)<6 and prio<6:score+=11
        if kind=='loot':
            score+=12*len(set(ITEM_TAGS.get(label,()))&tags)
            if label in run.equipped_rings+run.equipped_trinkets or label==run.equipped_amulet:score+=18
        eligible.append((score,quality,-c.index,c,label,'passive' if passive else 'core'))
    if eligible:
        score,quality,_n,c,label,group=max(eligible)
        return Action('pick',c.index,label,round(score,1),
                      f'{c.rarity} x{RARITY_MULTIPLIER[c.rarity]:g} • {group} • OCR {quality:.0%}')
    # All cards were read, but none fit the build and rarity strategy.
    # Banish only explicitly named unwanted jewellery; never banish a desired card.
    if kind=='loot' and policy.auto_banish and run.banishes<policy.max_banish_per_run:
        for c in cards:
            hit=best_named_match(c,blocked_names,policy.min_confidence)
            if not hit or clean(hit[1]) in run.used_banish: continue
            count=(parse_banish_count(controls.banish_texts[c.index-1])
                   if len(controls.banish_texts)>=c.index else None)
            if count is not None and count>0:
                return Action('banish',c.index,hit[1],reason=f'Explicitly blocked jewellery; {count} banishes left')
    if policy.auto_free_reroll and rerolls is not None and rerolls>policy.max_rerolls_reserved:
        return Action('reroll',reason=f'No acceptable offer; {rerolls} verified FREE rerolls remain')
    if policy.auto_skip and skip_is_available(controls.skip_text):
        if rerolls==0:
            return Action('skip',reason='Reroll explicitly costs gold; collect skip gold')
        if rerolls is not None and rerolls<=policy.max_rerolls_reserved:
            return Action('skip',reason='Preserve reserved free rerolls; skip this offer')
    return Action('wait',reason='No eligible card and no verified safe action')

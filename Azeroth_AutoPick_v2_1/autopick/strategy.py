"""Transparent, fail-closed card strategy for Azeroth Survivors.

All decisions here use visible OCR and user preferences. This is a rules engine,
not a trained model, and it cannot see unseen game state or drop probabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Sequence

from .engine import clean, match_quality

RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary")
RARITY_RANK = {name.lower(): i for i, name in enumerate(RARITIES)}
RARITY_BONUS = {"common": 0, "uncommon": 16, "rare": 40, "epic": 70, "legendary": 100}


@dataclass(frozen=True)
class OfferedCard:
    index: int
    lines: tuple[str, ...]
    rarity: str | None
    confidence: float = 1.0
    upgrade: bool = False


@dataclass(frozen=True)
class Controls:
    reroll_text: str = ""
    skip_text: str = ""
    banish_texts: tuple[str, ...] = ()
    # One or more controls may not be readable; NEVER assume missing means free.


@dataclass(frozen=True)
class Action:
    kind: str  # pick / reroll / skip / banish / wait
    index: int = 0
    label: str = ""
    score: float = 0.0
    reason: str = ""


def detect_rarity(lines: Sequence[str]) -> str | None:
    """Require an explicit rarity label; do not infer from a coloured border."""
    for line in lines[:5]:
        words = clean(line).split()
        for label in RARITIES:
            if label.lower() in words:
                return label
    return None


def parse_offers(cards: Sequence[Sequence[str]]) -> list[OfferedCard]:
    result = []
    for i, lines in enumerate(cards, 1):
        cleaned = tuple(str(x) for x in lines if clean(x))
        low = " ".join(clean(x) for x in cleaned[:6])
        is_upgrade = bool(re.search(r"\brank\s*\d+\b", low))
        result.append(OfferedCard(i, cleaned, detect_rarity(cleaned), upgrade=is_upgrade))
    return result


def parse_free_rerolls(text: str) -> int | None:
    """Return remaining free charges, 0 if explicitly gold-priced, None if unclear.

    e.g. 'Reroll 4 [R]' => 4; 'Reroll 100 gold [R]' => 0.
    Never guess from a bare number, since the number might be a gold price.
    """
    value = clean(text)
    if not re.search(r"\b(re+roll|reload|redraw)\b", value):
        return None
    if re.search(r"\b(gold|coins?|purchase|buy)\b", value):
        return 0
    m = re.search(r"\b(?:reroll|reload|redraw)\s+(\d{1,2})\b", value)
    if not m:
        return None
    count = int(m.group(1))
    return count if 0 <= count <= 9 else None


def skip_is_available(text: str) -> bool:
    return bool(re.search(r"\bskip\b", clean(text)))


def parse_banish_count(text: str) -> int | None:
    v = clean(text)
    m = re.search(r"\bbanish\s*(\d)\b", v)
    return int(m.group(1)) if m else None


def best_named_match(card: OfferedCard, rules: Sequence[str], threshold: float) -> tuple[int, str, float] | None:
    best = None
    for pos, name in enumerate(rules):
        quality = match_quality(name, card.lines)
        if quality >= threshold and (best is None or pos < best[0]):
            best = (pos, name, quality)
    return best


def is_avoided(card: OfferedCard, avoided: Sequence[str], threshold: float) -> bool:
    return any(match_quality(rule, card.lines) >= threshold for rule in avoided)


def select_action(kind: str, cards: Sequence[OfferedCard], controls: Controls,
                  preferences: Sequence[str], avoided: Sequence[str],
                  banish_targets: Sequence[str], *,
                  min_rarity: str = "Rare", min_confidence: float = 0.88,
                  use_free_rerolls: bool = True, auto_skip: bool = True,
                  auto_banish_jewelry: bool = True,
                  rarity_weight: float = 1.0) -> Action:
    """Pick eligible high-quality offers, else banish -> free reroll -> skip.

    No API call, keyboard/mouse use, OCR or side effects happen here.
    The engine deliberately refuses to act on unreadable card labels or buttons.
    """
    if kind not in ("level", "loot") or len(cards) not in (3, 4):
        return Action("wait", reason="Unknown choice screen")
    if len({c.index for c in cards}) != len(cards):
        return Action("wait", reason="Duplicate card positions")
    floor = RARITY_RANK.get(clean(min_rarity))
    if floor is None:
        return Action("wait", reason="Invalid rarity setting")
    # First look for a good, user-preferred offer that passes the rarity floor.
    eligible = []
    for card in cards:
        if not card.lines:
            continue
        if card.rarity is None:
            continue
        if RARITY_RANK[card.rarity.lower()] < floor:
            continue
        if is_avoided(card, avoided, min_confidence):
            continue
        match = best_named_match(card, preferences, min_confidence)
        if match is None:
            continue
        pos, label, quality = match
        # A high rarity can beat an adjacent priority, not the entire build plan.
        value = 150 - (pos * 13) + RARITY_BONUS[card.rarity.lower()] * rarity_weight
        if card.upgrade:
            value += 8
        eligible.append((value, -pos, quality, -card.index, card, label))
    if eligible:
        value, _prio, quality, _idx, card, label = max(eligible)
        return Action("pick", card.index, label, value,
                      f"{card.rarity} • {quality:.0%} name match")

    # If OCR cannot read the offered cards, don't waste rerolls or skip potentially
    # desirable cards that were simply unreadable.
    if any(not c.lines or c.rarity is None for c in cards):
        return Action("wait", reason="One or more cards/rarities unreadable")

    # Banish is limited and should only be spent on explicit unwanted jewellery,
    # never while an eligible pick exists and never on spells.
    if kind == "loot" and auto_banish_jewelry and banish_targets:
        for card in cards:
            hit = best_named_match(card, banish_targets, min_confidence)
            if hit and len(controls.banish_texts) >= card.index:
                left = parse_banish_count(controls.banish_texts[card.index - 1])
                if left and left > 0:
                    return Action("banish", card.index, hit[1], reason=f"Unwanted jewellery • {left} banishes shown")

    free = parse_free_rerolls(controls.reroll_text)
    if use_free_rerolls and free is not None and free > 0:
        return Action("reroll", reason=f"No eligible {min_rarity}+ preferred card • {free} free rerolls shown")
    if auto_skip and skip_is_available(controls.skip_text) and free == 0:
        return Action("skip", reason="No eligible card; reroll explicitly costs gold")
    # If the reroll button was unreadable/ambiguous, do not assume it's free OR
    # assume its charges are exhausted. Wait for human intervention.
    return Action("wait", reason="No eligible card; free reroll status not verified")


def action_fingerprint(kind: str, cards: Sequence[OfferedCard], controls: Controls) -> str:
    """Include counters to avoid clicking twice while waiting for a UI transition."""
    slots = [f"{c.index}:{clean(' '.join(c.lines[:5]))}:{clean(c.rarity or '')}" for c in cards]
    ctrl = [controls.reroll_text, controls.skip_text] + list(controls.banish_texts)
    return kind + "|" + "|".join(slots) + "|" + "|".join(clean(s) for s in ctrl)

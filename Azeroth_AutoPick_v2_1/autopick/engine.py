"""Pure selection rules, independently testable without a running game."""
from __future__ import annotations
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Sequence


def clean(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def parse_names(multiline: str) -> list[str]:
    """One item per line. Lines beginning with # are comments."""
    out = []
    for line in multiline.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def match_quality(rule: str, text_lines: Sequence[str]) -> float:
    """Match near the top of a card so descriptions don't masquerade as names.

    The first four OCR rows may include a hotkey, rarity, name and subtitle.
    A four-word item name can span multiple rows. Short names require exact words.
    """
    target = clean(rule)
    if not target or not text_lines:
        return 0.0
    start = [clean(s) for s in text_lines[:4] if clean(s)]
    joined = " ".join(start)
    pattern = r"(?<![a-z0-9])" + re.escape(target) + r"(?![a-z0-9])"
    if re.search(pattern, " ".join(start[:3])):
        return 1.0
    if re.search(pattern, joined):
        # OCR row 4 may already be description text. Accept if the name begins
        # in earlier rows, but refuse a name which appears only in description.
        if len(start) >= 4 and re.search(pattern, start[3]):
            return 0.70
        return 1.0
    if len(target) < 7:
        return 0.0
    words = target.split()
    seen = joined.split()
    n = len(words)
    best = 0.0
    # Compare against contiguous sequences, allowing an OCR-split word.
    for size in range(max(1, n - 1), min(len(seen), n + 2) + 1):
        for i in range(len(seen) - size + 1):
            phrase = " ".join(seen[i:i + size])
            ratio = SequenceMatcher(None, target, phrase).ratio()
            if ratio > best:
                best = ratio
    if len(start) >= 4 and best > 0.70:
        # If the first word of the target starts only in the last row,
        # it is much more likely to be a description than the card title.
        first_word = words[0]
        if not any(re.search(r"\b" + re.escape(first_word) + r"\b", row) for row in start[:3]):
            return min(best, 0.70)
    return best


@dataclass(frozen=True)
class Decision:
    kind: str
    index: int
    rule: str
    score: float
    reason: str


def best_choice(kind: str, cards: list[list[str]], priorities: list[str], ignored: list[str],
                min_confidence: float = 0.88, fallback: str = "wait") -> Decision | None:
    """Choose the earliest matching preference. No preference match => wait by default.

    This only sees OCR strings and never alters game state itself.
    """
    if kind not in ("level", "loot") or len(cards) < 2:
        return None
    available = []
    for idx, lines in enumerate(cards):
        # Require at least some actual visible text per card before doing anything.
        if not any(clean(x) for x in lines):
            continue
        if any(match_quality(avoid, lines) >= min_confidence for avoid in ignored):
            continue
        available.append(idx)
    for priority in priorities:
        candidates = [(match_quality(priority, cards[i]), i) for i in available]
        if not candidates:
            break
        score, idx = max(candidates, default=(0.0, -1))
        if score >= min_confidence:
            return Decision(kind, idx + 1, priority, score, "priority")
    if fallback == "first" and len(available) == len(cards):
        return Decision(kind, available[0] + 1, "(unlisted first card)", 1.0, "fallback")
    return None


def popup_hint(text: str) -> str | None:
    t = clean(text)
    if re.search(r"\b(level up|choose an ability|choose a spell|upgrade a spell)\b", t):
        return "level"
    if re.search(r"\b(jewelry|jewellery|cache|amulet|trinket|guardian s lair|choose a ring|choose one piece)\b", t):
        return "loot"
    return None


def card_fingerprint(kind: str, cards: list[list[str]]) -> str:
    return kind + ":" + "|".join(" ".join(clean(x) for x in rows[:4]) for rows in cards)

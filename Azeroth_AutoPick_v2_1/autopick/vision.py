"""Fast, calibration-free observer of the VISIBLE Windows game screen.

Does not interact with the game, game memory, or network. Call from a worker
thread. The selected action is an advisory proposal until the GUI approves it.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from PIL import Image
from .capture import capture_window, Reader
from .layout import find_cards, footer_crop, footer_controls, split_ocr_rows, DetectedLayout
from .strategy import Action, Controls, parse_offers, action_fingerprint
from .advanced import Policy, RunState, choose, SPELL_MEMBERSHIP
from .catalog import LEGENDARY_AMULETS
from .engine import popup_hint, clean, match_quality
from .visual import reroll_visual_state


@dataclass
class Scan:
    kind: str|None
    header: str
    cards: list[list[str]]
    rarities: list[str]
    controls: Controls
    decision: Action
    signature: str|None
    layout: DetectedLayout|None
    layout_source: str
    is_verified: bool
    inferred_class: str|None
    free_reroll_guard: str
    banish_points: tuple[tuple[int,int]|None, ...] = ()


class VisionScanner:
    def __init__(self):
        self.reader:Reader|None=None
        self.last_snapshot:np.ndarray|None=None
        self.cached:Scan|None=None
        self.last_window:int|None=None
        self.cache_context:str|None=None
        self.ocr_calls=0

    @staticmethod
    def _fingerprint(img:Image.Image):
        # Only non-animated parts of the choice UI: title, card names, and
        # footer. Coarsening pixels makes the comparison robust to HUD motion.
        w,h=img.size
        regions=((.32,.10,.68,.23),(.19,.45,.82,.57),(.22,.78,.83,.89))
        chips=[]
        for x1,y1,x2,y2 in regions:
            c=img.crop((int(x1*w),int(y1*h),int(x2*w),int(y2*h)))
            chips.append(np.asarray(c.resize((96,30)).convert('L'),dtype=np.uint8))
        return np.concatenate(chips,axis=0)

    @staticmethod
    def _similar(a:np.ndarray|None,b:np.ndarray):
        if a is None or a.shape!=b.shape:return False
        return float(np.mean(np.abs(a.astype(np.int16)-b.astype(np.int16))))<1.4

    @staticmethod
    def infer_class(cards,confidence=.91):
        scores={}
        # Two separately recognised spells are required for a meaningful
        # class guess. This is advisory; it never silently changes a profile.
        for c in cards:
            matched=set()
            for spell,classes in SPELL_MEMBERSHIP.items():
                if match_quality(spell,c.lines)>=confidence:
                    matched.update(classes)
            for cls in matched:scores[cls]=scores.get(cls,0)+1
        ordered=sorted(scores.items(),key=lambda p:p[1],reverse=True)
        return ordered[0][0] if ordered and ordered[0][1]>=2 and (len(ordered)==1 or ordered[0][1]>ordered[1][1]) else None

    def scan(self,hwnd:int,settings:dict,profile:dict,run:RunState)->Scan:
        shot=capture_window(hwnd)
        image=shot.image
        fp=self._fingerprint(image)
        # A change in settings, build, or inferred items must invalidate any
        # cached decision even if the card art itself has not changed.
        context=repr((settings, profile, run.as_dict(), sorted(run.used_banish)))
        if (hwnd==self.last_window and self.cached is not None and
                context==self.cache_context and self._similar(self.last_snapshot,fp)):
            return self.cached
        self.last_window=hwnd
        self.cache_context=context
        self.last_snapshot=fp
        # Four-card Opening Hand needs precedence: a 3-card detector could
        # otherwise mistake the first three of four for the full choice.
        layout=find_cards(image,4)
        if layout is None:
            layout=find_cards(image,3)
        if layout is None:
            self.cached=Scan(None,'',[],[],Controls(),Action('wait',reason='No choice cards'),None,None,'none',False,None,'unknown')
            return self.cached
        if self.reader is None:self.reader=Reader()
        def ocr(img):
            self.ocr_calls+=1
            return self.reader.read(img)
        w,h=image.size
        header_area=image.crop((int(w*.295),int(h*.078),int(w*.705),int(h*.272)))
        hdr=ocr(header_area)
        header=' '.join(str(r[2]) for r in hdr)
        kind=popup_hint(header)
        if not kind:
            self.cached=Scan(None,header,[],[],Controls(),Action('wait',reason='Unidentified popup'),None,layout,'detected',False,None,'unknown')
            return self.cached
        # Titles and rarities are roughly 37%-58% down the card. The detector
        # measures their location each time, regardless of window resolution.
        y1=max(0,int(layout.top+layout.cards[0].height*.365))
        y2=min(h,int(layout.top+layout.cards[0].height*.585))
        region=(max(0,layout.left-7),y1,min(w,layout.right+7),y2)
        raw=ocr(image.crop(region))
        cards=split_ocr_rows(raw,region,layout)
        # Legendary-family names are reused for different spell variants.
        # Only read descriptions for these high-risk choices so ordinary
        # level-ups retain the fast batched OCR path.
        if kind=='loot':
            legendary_names={clean(n) for n in LEGENDARY_AMULETS}
            for i,rows in enumerate(cards):
                if not any(match_quality(n, rows) >= .94 for n in legendary_names):
                    continue
                box=layout.cards[i]
                desc=image.crop((box.left+8, int(box.top+box.height*.54),
                                 box.right-8, int(box.top+box.height*.87)))
                for entry in ocr(desc):
                    value=str(entry[2]).strip()
                    if value: rows.append(value)
        offered=parse_offers(cards)
        # Footer is read even when a candidate is good, so a changed reroll
        # counter alters the signature and pending-action acknowledgement.
        footer_img, footer_rect=footer_crop(image,layout)
        footer=ocr(footer_img)
        reroll_text,skip_text,banishes,reroll_pt,banish_pts=footer_controls(footer,footer_rect,layout)
        controls=Controls(reroll_text,skip_text,banishes)
        pol=Policy.from_dict(settings)
        decision=choose(kind,offered,controls,profile,pol,run)
        guard='not requested'
        if decision.kind=='reroll':
            guard=reroll_visual_state(image,around=reroll_pt) if reroll_pt else 'unknown'
            if guard!='free-looking':
                decision=Action('wait',reason='Reroll colour safety check did not confirm FREE (saw: '+guard+')')
        if decision.kind=='banish' and (len(banish_pts)<decision.index or banish_pts[decision.index-1] is None):
            decision=Action('wait',reason='Banish button position not safely detected')
        if kind=='loot' and layout.confidence<.83:
            decision=Action('wait',reason='Jewellery card-border layout is uncertain')
        sig=action_fingerprint(kind,offered,controls)
        self.cached=Scan(kind,header,cards,[c.rarity or '?' for c in offered],controls,decision,
                         sig,layout,'detected borders',layout.confidence>.82,self.infer_class(offered),guard,banish_pts)
        return self.cached

    def invalidate(self):
        self.last_snapshot=None
        self.cache_context=None
        self.cached=None

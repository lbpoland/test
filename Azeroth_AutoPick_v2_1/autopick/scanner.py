"""OCR bridge for Azeroth Survivors: automatic cards + safe control detection.

This code does not read or modify game memory. All game facts here are derived
from the visible screenshot, and uncertain inputs cause a WAIT decision.
"""
from __future__ import annotations

from .capture import capture_window, Reader
from .catalog import infer_class
from .engine import popup_hint
from .layout import find_cards, ocr_region, footer_crop, footer_controls, split_ocr_rows
from .strategy import Action, Controls, action_fingerprint, parse_offers, select_action
from .visual import reroll_visual_state


class GameScanner:
    def __init__(self, reader=None):
        self.reader=reader

    def scan(self, hwnd:int, settings:dict, profile:dict)->dict:
        if self.reader is None:
            self.reader=Reader()
        shot=capture_window(hwnd)
        blank={"kind":None,"header":"","cards":[],"decision":Action('wait',reason='No choice screen'),
               "signature":None,"rarities":[],"controls":Controls(),"layout":None,
               "banish_points":(),"class_guess":None,"class_hits":0,"window":(shot.left,shot.top),
               "layout_confidence":0.0}
        layout=find_cards(shot.image, expected=int(settings.get('card_count',3)))
        if layout is None:
            return blank
        blank['layout']=layout
        blank['layout_confidence']=layout.confidence
        # Read a small heading, only *after* finding the distinctive card layout.
        w,h=shot.image.size
        headline_crop=shot.image.crop((round(w*.30),round(h*.085),round(w*.70),
                                      max(round(h*.087)+10,layout.top-5)))
        headline=' '.join(r[2] for r in self.reader.read(headline_crop))
        kind=popup_hint(headline)
        if kind is None:
            blank['header']=headline
            blank['decision']=Action('wait',reason='Unknown popup heading: no automatic inputs')
            return blank
        blank['kind']=kind
        blank['header']=headline
        crop,region=ocr_region(layout,shot.image)
        rows=self.reader.read(crop)
        cards=split_ocr_rows(rows,region,layout)
        offered=parse_offers(cards)
        blank['cards']=cards
        blank['rarities']=[c.rarity or 'UNKNOWN' for c in offered]
        cls,hits=infer_class(cards)
        blank['class_guess']=cls
        blank['class_hits']=hits
        kwargs=dict(min_rarity=settings.get('min_rarity_level' if kind=='level' else 'min_rarity_loot','Rare'),
                    min_confidence=float(settings.get('min_confidence',.88)),
                    use_free_rerolls=bool(settings.get('use_free_rerolls',True)),
                    auto_skip=bool(settings.get('auto_skip',True)),
                    auto_banish_jewelry=bool(settings.get('auto_banish_jewelry',True)),
                    rarity_weight=float(settings.get('rarity_weight',1.0)))
        preferences=profile.get('level' if kind=='level' else 'loot',[])
        avoid=profile.get('avoid',[])
        banish=profile.get('banish_loot',[])
        blank['decision']=select_action(kind,offered,Controls(),preferences,avoid,banish,**kwargs)
        # When class recognition identifies a *different* class with >=2
        # independent matches, pause and request a profile switch before any
        # selection. The GUI can then re-scan with the matching build.
        if (kind=='level' and settings.get('auto_class',True) and cls and
            profile.get('class') and profile['class']!=cls):
            blank['decision']=Action('wait',reason='Detected '+cls+'; switch to the right class build')
            blank['signature']=action_fingerprint(kind,offered,Controls())
            return blank
        ctrl=Controls()
        if blank['decision'].kind!='pick':
            footer,region2=footer_crop(shot.image,layout)
            frows=self.reader.read(footer)
            reroll,skip,banish_texts,reroll_point,banish_points=footer_controls(frows,region2,layout)
            ctrl=Controls(reroll,skip,banish_texts)
            blank['banish_points']=banish_points
            blank['decision']=select_action(kind,offered,ctrl,preferences,avoid,banish,**kwargs)
            # Defence in depth: text must say *free*, and the visual check
            # must agree. A paid reroll is never sent, even on an OCR error.
            if blank['decision'].kind=='reroll':
                visual=reroll_visual_state(shot.image,around=reroll_point)
                if visual!='free-looking':
                    blank['decision']=Action('wait',reason='Reroll visual guard: '+visual+'; not spending gold')
        blank['controls']=ctrl
        blank['signature']=action_fingerprint(kind,offered,ctrl)
        return blank

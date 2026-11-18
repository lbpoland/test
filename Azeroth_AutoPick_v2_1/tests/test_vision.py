import sys
from unittest.mock import patch
import numpy as np
from PIL import Image
from autopick.vision import VisionScanner
from autopick.capture import Screen
from autopick.layout import find_cards
from autopick.advanced import RunState
from autopick.catalog import make_profiles
from autopick.visual import reroll_visual_state


def screen_paths():
    from pathlib import Path
    root=Path(__file__).resolve().parent.parent
    # Tests only use user-supplied screenshot fixtures when present. A source
    # release can still run tests without including these private screenshots.
    return list((root/'fixtures').glob('*.png'))


def test_layout_finds_actual_user_screen_borders():
    from pathlib import Path
    root=Path(__file__).resolve().parent.parent
    if not (root/'fixtures').exists():return
    for path in screen_paths():
        im=Image.open(path)
        layout=find_cards(im)
        assert layout is not None and len(layout.cards)==3
        assert layout.confidence>.90
        assert layout.cards[0].cx < layout.cards[1].cx < layout.cards[2].cx


def test_reroll_visual_second_factor_against_supplied_examples():
    from pathlib import Path
    root=Path(__file__).resolve().parent.parent
    first=root/'fixtures'/'free-rerolls.png';second=root/'fixtures'/'paid-rerolls.png'
    if not first.exists() or not second.exists():return
    assert reroll_visual_state(Image.open(first))=='free-looking'
    assert reroll_visual_state(Image.open(second))=='paid-looking'


def test_popup_suppression_if_no_card_outlines():
    blank=Image.new('RGB',(1536,960),'#000000')
    with patch('autopick.vision.capture_window',return_value=Screen(blank,0,0,1)):
        result=VisionScanner().scan(1,{},make_profiles()['Paladin — Consecration AoE'],RunState())
        assert result.kind is None and result.decision.kind=='wait'


def test_class_inference_from_two_independent_visible_spell_names():
    from autopick.strategy import parse_offers
    cs=parse_offers([['Uncommon','Hammer of Wrath'],['Rare','Exorcism'],['Common','Redemption']])
    assert VisionScanner.infer_class(cs)=='Paladin'
    cs=parse_offers([['Rare','Fireball'],['Rare','Unrecognized title'],['Common','Another item']])
    assert VisionScanner.infer_class(cs) is None


def _fake_read_factory(free=True):
    class FakeReader:
        def __init__(self):self.calls=0
        def read(self,im):
            self.calls+=1
            if self.calls==1:
                return [(.48,.49,'LEVEL UP!',.999)]
            if self.calls==2:
                cols=[.164,.50,.837]
                items=(('UNCOMMON','Hammer of Wrath'),('COMMON','Redemption'),('COMMON','Exorcism')) if free else (
                    ('COMMON','Consecration'),('COMMON','Hammer of Justice'),('COMMON','Hammer of Wrath'))
                out=[]
                for x,(rarity,name) in zip(cols,items):
                    out += [(x,.27,rarity,.99),(x,.46,name,.99),(x,.63,'New spell' if free else 'Rank 7 > 8',.99)]
                return sorted(out,key=lambda x:x[1])
            if self.calls==3:
                reroll='Reroll 4' if free else 'Reroll 100 gold'
                return [(.168,.18,'Banish (2)',.99),(.500,.18,'Banish (2)',.99),
                        (.832,.18,'Banish (2)',.99),(.57,.54,'Skip +11 gold',.99),
                        (.815,.54,reroll,.99)]
            raise AssertionError('Unexpected OCR pass')
    return FakeReader


def test_end_to_end_proposes_free_reroll_and_paid_skip_with_synthetic_ocr():
    from pathlib import Path
    root=Path(__file__).resolve().parent.parent
    free=root/'fixtures'/'free-rerolls.png'
    paid=root/'fixtures'/'paid-rerolls.png'
    if not free.exists() or not paid.exists():return
    cfg={'min_spell_rarity':'Rare','min_loot_rarity':'Rare'}
    prof=make_profiles()['Paladin — Consecration AoE']
    for file,isfree,expected in [(free,True,'reroll'),(paid,False,'skip')]:
        image=Image.open(file)
        with patch('autopick.vision.capture_window',return_value=Screen(image,0,0,1)), \
             patch('autopick.vision.Reader',_fake_read_factory(isfree)):
            scanner=VisionScanner()
            result=scanner.scan(1,cfg,prof,RunState())
            assert result.is_verified
            assert result.kind=='level'
            assert result.inferred_class=='Paladin'
            assert result.decision.kind==expected, (result.decision,result.controls)
            assert scanner.scan(1,cfg,prof,RunState()) is result  # unchanged snapshot avoids repeated OCR

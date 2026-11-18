from autopick.catalog import SPELLS,RINGS,TRINKETS,AMULETS,LEGENDARY_AMULETS,make_profiles
from autopick.autolayout import auto_layout,card_title_crop
from PIL import Image

def test_all_nine_classes_complete():
    assert len(SPELLS)==9
    assert sum(map(len,SPELLS.values()))>=103
    assert len(make_profiles())==27
    assert len(RINGS)==9 and len(TRINKETS)==14
    assert len(AMULETS)==20 and len(LEGENDARY_AMULETS)==15

def test_profiles_are_valid_class_spells():
    for key,p in make_profiles().items():
        assert p['class'] in SPELLS
        assert 5<=len(p['level'])<=6
        assert set(p['level']).issubset(set(SPELLS[p['class']]))
        assert all(x in RINGS+TRINKETS+AMULETS+LEGENDARY_AMULETS for x in p['loot'])
        assert p['policy']['allow_gold_rerolls'] is False

def test_autolayout_known_screenshot_geometry():
    layout=auto_layout(Image.new('RGB',(2048,1280),'black'))
    assert len(layout.cards)==3
    assert abs((layout.cards[1][0]+layout.cards[1][2])/2-.5)<.01
    crop=card_title_crop(Image.new('RGB',(2048,1280),'black'),layout.cards[0])
    assert crop.size[0]>100 and crop.size[1]>70

"""Visual second factor for a FREE reroll, on the actual detected control."""
from __future__ import annotations
import numpy as np
from PIL import Image


def reroll_visual_state(screen: Image.Image, around:tuple[int,int]|None=None)->str:
    """Return free-looking, paid-looking or unknown, never a purchase decision.

    Gold/yellow free-reroll text and red paid-reroll price are observed in the
    user's Nov 3 screenshots. Both this guard and explicit OCR text are needed.
    """
    w,h=screen.size
    if around is not None:
        x,y=around
        xa=max(0,int(x-w*.065)); xb=min(w,int(x+w*.087))
        ya=max(0,int(y-h*.025)); yb=min(h,int(y+h*.025))
    else:
        xa,xb=int(w*.63),int(w*.78)
        ya,yb=int(h*.834),int(h*.884)
    rgb=np.asarray(screen.crop((xa,ya,xb,yb)).convert('RGB'),dtype=np.int16)
    if rgb.size==0:return 'unknown'
    red,green,blue=(rgb[:,:,i] for i in range(3))
    red_text=(red>135)&(red>green*1.5)&(green<135)&(blue<110)
    golden_text=(red>130)&(green>95)&(red<green*2)&(blue<130)
    red_share=float(np.mean(red_text)); gold_share=float(np.mean(golden_text))
    if red_share>.002:return 'paid-looking'
    if red_share<.001 and gold_share>.003:return 'free-looking'
    return 'unknown'

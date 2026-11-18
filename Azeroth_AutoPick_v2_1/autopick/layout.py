"""Find the Azeroth Survivors card screen by its *visible* rectangle borders.

No setup or saved pixel coordinates. Detected bounds are re-computed on every
popup, so changing resolution, game/window size or display DPI is supported
as long as the actual game UI and its card borders stay visible. The detector
fails closed if an unfamiliar layout is encountered.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from PIL import Image

@dataclass(frozen=True)
class CardRect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def cx(self) -> int:
        return (self.left + self.right) // 2

    @property
    def cy(self) -> int:
        return (self.top + self.bottom) // 2

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

@dataclass(frozen=True)
class DetectedLayout:
    cards: tuple[CardRect, ...]
    confidence: float

    @property
    def top(self) -> int:
        return min(c.top for c in self.cards)

    @property
    def bottom(self) -> int:
        return max(c.bottom for c in self.cards)

    @property
    def left(self) -> int:
        return min(c.left for c in self.cards)

    @property
    def right(self) -> int:
        return max(c.right for c in self.cards)


def _clusters(indices: np.ndarray, max_gap: int = 8) -> list[tuple[int, int]]:
    if len(indices) == 0:
        return []
    start = prev = int(indices[0])
    result = []
    for index in indices[1:]:
        index = int(index)
        if index - prev > max_gap:
            result.append((start, prev))
            start = index
        prev = index
    result.append((start, prev))
    return result


def _grey(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert('RGB'), dtype=np.uint8)
    return a[:,:,0].astype(np.int16)*0.299 + a[:,:,1].astype(np.int16)*0.587 + a[:,:,2].astype(np.int16)*0.114


def find_cards(img: Image.Image, expected: int = 3) -> DetectedLayout | None:
    """Detect 3 or 4 card rectangles from their long vertical/horizontal outlines.

    No OCR is required. A full-screen game screenshot may be 2048x1280 or
    another size; measurements are relative to the visible game window.
    """
    if expected not in (3, 4):
        return None
    g = _grey(img)
    h, w = g.shape
    if w < 600 or h < 420:
        return None
    # Cards' vertical side edges dominate the centre of a choice popup.
    low_y, high_y = int(.36*h), int(.70*h)
    sample = g[low_y:high_y]
    if sample.shape[0] < 100:
        return None
    strengths = (np.abs(np.diff(sample, axis=1)) > 23).mean(axis=0)
    xs = np.where((strengths > 0.78) & (np.arange(len(strengths)) > .09*w) &
                  (np.arange(len(strengths)) < .91*w))[0]
    bands = _clusters(xs, max_gap=max(5,int(w*.004)))
    boundaries = [(a+b)//2 for a,b in bands if b-a <= .023*w]
    if len(boundaries) < expected*2:
        return None

    # Find N consecutive pairs of long edges, with matching widths and gaps.
    # The image contains arbitrary other widgets; verify the full pattern.
    candidates = []
    for k in range(len(boundaries)-2*expected+1):
        vals = boundaries[k:k+2*expected]
        widths = [vals[i*2+1]-vals[i*2] for i in range(expected)]
        gaps = [vals[i*2+2]-vals[i*2+1] for i in range(expected-1)]
        if not all(.115*w < s < .26*w for s in widths):
            continue
        if not all(.008*w < s < .073*w for s in gaps):
            continue
        mean_width = float(np.mean(widths))
        if max(abs(a-mean_width) for a in widths) > .08*mean_width:
            continue
        if vals[0] < .08*w or vals[-1] > .92*w:
            continue
        score = 1.0 - abs((vals[0]+vals[-1])/2-w/2)/w - np.std(widths)/w
        candidates.append((score, vals))
    if not candidates:
        return None
    score, vals = max(candidates, key=lambda it:it[0])
    # Long horizontal edges across the INSIDE of all cards identify the real
    # top and bottom; do not confuse decorative lines within card descriptions.
    row_scores=[]
    y0, y1 = int(h*.15), int(h*.89)
    for i in range(expected):
        l,r=vals[2*i]+8, vals[2*i+1]-8
        stripe=g[y0:y1,l:r]
        if stripe.shape[1]<80:
            return None
        row_scores.append((np.abs(np.diff(stripe,axis=0)) > 23).mean(axis=1))
    rows=np.mean(row_scores,axis=0)
    ys=np.where(rows>.82)[0]+y0
    ybands=_clusters(ys,max_gap=max(5,int(h*.006)))
    centers=[(a+b)//2 for a,b in ybands]
    vertical_pairs=[]
    for i,a in enumerate(centers):
        for b in centers[i+1:]:
            if .34*h < b-a < .65*h:
                # Card rows appear in central 20%-90% of the image.
                vertical_pairs.append((abs((a+b)/2-.52*h)/h,a,b))
    if not vertical_pairs:
        return None
    _, top, bottom=min(vertical_pairs,key=lambda k:k[0])
    rectangles=tuple(CardRect(vals[i*2], top, vals[i*2+1], bottom) for i in range(expected))
    return DetectedLayout(rectangles, float(max(0.0,min(1.0,score))))


def normalized_crop(img: Image.Image, rect: tuple[float,float,float,float]) -> Image.Image:
    w,h=img.size
    return img.crop((round(rect[0]*w),round(rect[1]*h),round(rect[2]*w),round(rect[3]*h)))


def ocr_region(layout: DetectedLayout, img: Image.Image) -> tuple[Image.Image, tuple[int,int,int,int]]:
    """One OCR capture for all card labels + rank tags, not long descriptions."""
    h=img.height
    region=(max(0,layout.left-9),max(0,layout.top-4),
            min(img.width,layout.right+9),min(h,int(layout.top+layout.cards[0].height*.58)))
    return img.crop(region),region


def split_ocr_rows(rows: Sequence[tuple[float,float,str,float]],
                   region: tuple[int,int,int,int], layout: DetectedLayout) -> list[list[str]]:
    a,b,c,d=region
    out=[[] for _ in layout.cards]
    for x,y,text,confidence in rows:
        px=a+x*(c-a)
        for i,box in enumerate(layout.cards):
            if box.left-6<=px<=box.right+6:
                out[i].append((y,text))
                break
    return [[t for _y,t in sorted(items)] for items in out]


def footer_crop(img: Image.Image, layout: DetectedLayout) -> tuple[Image.Image,tuple[int,int,int,int]]:
    # Button rows are immediately below the card borders.
    x1=max(0,layout.left-25)
    x2=min(img.width,layout.right+25)
    y1=min(img.height-1,layout.bottom+6)
    y2=min(img.height, layout.bottom+int(img.height*.18))
    if y2-y1<25:
        y2=min(img.height,y1+25)
    return img.crop((x1,y1,x2,y2)),(x1,y1,x2,y2)


def footer_controls(rows: Sequence[tuple[float,float,str,float]], region:tuple[int,int,int,int],
                    layout:DetectedLayout) -> tuple[str,str,tuple[str,...],tuple[int,int] | None,tuple[tuple[int,int] | None,...]]:
    """Read controls by name+position, not by guessed pixel coordinates.

    Return reroll text, skip text, 3 banish texts, reroll centre, banish centres.
    When the controls cannot be identified, coordinates are None (never click).
    """
    from .engine import clean
    a,b,c,d=region
    words=[(a+x*(c-a),b+y*(d-b),str(t)) for x,y,t,conf in rows]
    banish=[[] for _ in layout.cards]
    banish_positions=[None for _ in layout.cards]
    reroll=[]; skip=[]; reroll_point=None
    # OCR often separates 'Reroll', '4', 'R' into individual boxes, so group
    # nearby words on the same button by position relative to the first word.
    for x,y,t in words:
        norm=clean(t)
        if 'banish' in norm:
            j=min(range(len(layout.cards)),key=lambda k:abs(x-layout.cards[k].cx))
            if abs(x-layout.cards[j].cx)<layout.cards[j].width*.44:
                banish[j].append(t)
                banish_positions[j]=(int(layout.cards[j].cx),int(y))
        if any(k in norm for k in ('reroll','redraw','reload')):
            if x>layout.cards[0].cx and y>layout.bottom+imgsafe(layout):
                reroll.append((x,y,t))
                reroll_point=(int(x),int(y))
        if 'skip' in norm and y>layout.bottom:
            skip.append((x,y,t))
    def combine(base):
        if not base: return ''
        x=sum(v[0] for v in base)/len(base); y=sum(v[1] for v in base)/len(base)
        return ' '.join(t for wx,wy,t in sorted(words,key=lambda p:p[0])
                        if abs(wy-y)<max(16,(d-b)*.11) and abs(wx-x)<(c-a)*.16)
    # Recognised reroll row must start at Reroll; do not accept an isolated 4.
    text_r=combine(reroll)
    text_s=combine(skip)
    for i,items in enumerate(banish):
        if banish_positions[i]:
            x,y=banish_positions[i]
            banish[i]=[t for wx,wy,t in words if abs(wx-x)<layout.cards[i].width*.40 and abs(wy-y)<20]
    return text_r,text_s,tuple(' '.join(z) for z in banish),reroll_point,tuple(banish_positions)


def imgsafe(layout:DetectedLayout)->int:
    return max(1,int(layout.cards[0].height*.07))

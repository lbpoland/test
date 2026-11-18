"""Automatic three-card geometry, no per-session manual calibration.
Estimates the light vertical borders of the three cards, with screenshot-layout
fallback. Coordinates are fractions of the captured game WINDOW, not desktop.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from PIL import Image

@dataclass(frozen=True)
class Layout:
    cards: tuple[tuple[float,float,float,float], ...]
    source: str
    certainty: float

# 2048x1280 screenshot samples provided Nov 3, 2026; normalized layout.
SCREENSHOT = ((.184,.283,.381,.758),(.401,.283,.598,.758),(.618,.283,.816,.758))

def auto_layout(img: Image.Image) -> Layout:
    """Locate card edges; don't infer extra cards from background textures."""
    w,h = img.size
    if w < 700 or h < 450:
        return Layout(SCREENSHOT, 'screenshot-preset', .65)
    small = img.resize((768,480), Image.Resampling.BILINEAR).convert('RGB')
    a = np.asarray(small, dtype=np.int16)
    # Card borders are neutral pale grey over darker textured backgrounds.
    # Scan vertical strokes between 35-70% of the height, avoiding card text.
    scan = a[int(480*.35):int(480*.70)]
    mx=np.max(scan,axis=2); mn=np.min(scan,axis=2)
    neutral=(mn>78)&((mx-mn)<42)
    column=neutral.mean(axis=0)
    # Detect pairs of left/right borders close to the known row proportions.
    x0s=[.184,.381,.401,.598,.618,.816]
    edges=[]; strengths=[]
    for expected in x0s:
        mid=int(expected*768); radius=int(.045*768)
        lo=max(0,mid-radius); hi=min(768,mid+radius+1)
        j=lo+int(column[lo:hi].argmax())
        edges.append(j/768); strengths.append(float(column[j]))
    good=(all(abs(e-v)<.035 for e,v in zip(edges,x0s))
          and all(edges[i+1]>edges[i]+.012 for i in range(5))
          and min(strengths)>.26)
    if not good:
        return Layout(SCREENSHOT,'screenshot-preset',.70)
    cards=[]
    for i in range(3):
        left,right=edges[2*i:2*i+2]
        if not .15 < right-left < .25:
            return Layout(SCREENSHOT,'screenshot-preset',.70)
        cards.append((left,.283,right,.758))
    return Layout(tuple(cards),'border-detection',.92)

def card_title_crop(img: Image.Image, box: tuple[float,float,float,float]) -> Image.Image:
    """Name, rarity, rank, NEW, but not paragraphs of descriptions."""
    w,h=img.size; x1,y1,x2,y2=box
    return img.crop((int((x1+.026)*w),int(.475*h),int((x2-.026)*w),int(.551*h)))

def card_top_crop(img: Image.Image, box: tuple[float,float,float,float]) -> Image.Image:
    w,h=img.size; x1,y1,x2,y2=box
    return img.crop((int((x1+.028)*w),int(.285*h),int((x2-.025)*w),int(.325*h)))

def centers(layout: Layout):
    return tuple((l+r)/2 for l,t,r,b in layout.cards)

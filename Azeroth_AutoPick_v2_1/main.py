"""Azeroth AutoPick v2 — optional local Windows companion.

Original hand-drawn UI in a dark fantasy style. No game art, trademark imagery,
process injection, account login, game memory reads, or remote requests.
"""
from __future__ import annotations
import copy
import ctypes
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, simpledialog
import tkinter as tk

from autopick.controller_base import AutoPickBase as LegacyUI, load_json, save_json
from autopick.catalog import (SPELLS, RINGS, TRINKETS, AMULETS,
                              LEGENDARY_AMULETS, make_profiles)
from autopick.capture import foreground_window, key_down, title_of
from autopick.windows import (inspect_window, discover_game_windows,
                              choose_unambiguous, GameWindow)
from autopick.engine import clean, parse_names
from autopick.advanced import (Policy, RunState, PASSIVES, ITEM_TAGS,
                               make_passive_plan, RARITY_MULTIPLIER)
from autopick.vision import VisionScanner
from autopick.guides import enrich_profiles
from autopick.amulets import SPELL_AMULETS
from autopick.strategy import RARITIES

BASE=Path(__file__).resolve().parent
BG='#0c0b0a'; SHADE='#15120e'; PANEL='#211a13'; DARK='#100e0c'
BORDER='#644626'; GOLD='#e5bd73'; DIM_GOLD='#a17a46'; CREAM='#f2e6ca'
MUTED='#b7a58a'; BLACK='#080706'; GREEN='#77c993'; RED='#e67a68'
RARE={'Common':'#c6c6c7','Uncommon':'#48dc5b','Rare':'#4e91ff',
      'Epic':'#bd74f7','Legendary':'#f7ae42','?':'#797266'}


def title_label(parent,text,size=14,color=GOLD,**kw):
    return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                    font=('Georgia',size,'bold'),**kw)

def txt_label(parent,text,size=10,color=MUTED,**kw):
    return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                    font=('Segoe UI',size),**kw)

def panel(parent,**kw):
    return tk.Frame(parent,bg=PANEL,highlightbackground=BORDER,
                    highlightthickness=1,**kw)

def styled_button(parent,text,command,primary=False,width=None):
    params=dict(text=text,command=command,font=('Georgia',11,'bold'),
                relief='flat',cursor='hand2',bd=1,padx=12,pady=5,
                activeforeground=CREAM,activebackground='#784c25')
    if width: params['width']=width
    if primary:
        params.update(bg='#765021',fg='#fff0cc',highlightbackground=GOLD)
    else:
        params.update(bg='#302216',fg=GOLD,highlightbackground=BORDER)
    return tk.Button(parent,**params)


class RuneBadge(tk.Canvas):
    def __init__(self,parent):
        super().__init__(parent,width=66,height=66,bg=BG,highlightthickness=0)
        self.create_oval(3,3,63,63,outline=DIM_GOLD,width=3)
        self.create_oval(10,10,56,56,outline='#89632d',width=1)
        self.create_polygon(33,13,50,49,39,45,34,33,27,48,17,50,
                            fill='#bd8d42',outline=GOLD)
        self.create_text(33,36,text='A',font=('Georgia',26,'bold'),fill=CREAM)
        for x,y in ((33,5),(33,61),(5,33),(61,33)):
            self.create_oval(x-2,y-2,x+2,y+2,fill=GOLD,outline='')


class ChoiceCard(tk.Canvas):
    def __init__(self,parent,index):
        super().__init__(parent,width=205,height=198,bg=PANEL,
                         highlightthickness=0)
        self.index=index
        self.render('—','?','AWAITING CARDS',False,'')
    def render(self,name,rarity,small,active,subtitle):
        self.delete('all')
        w,h=205,198
        colour=RARE.get(rarity,RARE['?'])
        self.create_rectangle(3,3,w-3,h-3,fill='#161310',outline=colour if active else BORDER,width=2)
        self.create_rectangle(11,11,w-11,h-11,outline='#453425',width=1)
        self.create_line(35,26,w-35,26,fill=colour,width=1)
        self.create_oval(16,14,43,41,fill='#10100e',outline=colour,width=1)
        self.create_text(30,27,text=str(self.index),fill=CREAM,font=('Georgia',11,'bold'))
        self.create_text(102,52,text='✦',fill=colour,font=('Georgia',32))
        self.create_text(102,86,text=rarity.upper() if rarity!='?' else 'UNKNOWN',
                         fill=colour,font=('Segoe UI',10,'bold'))
        chunks=self._wrap(name,19)
        for i,line in enumerate(chunks[:2]):
            self.create_text(102,115+i*19,text=line,fill=CREAM,
                             font=('Georgia',14,'bold'))
        self.create_line(35,162,170,162,fill='#76532d')
        self.create_text(102,173,text=small[:29],fill=MUTED,font=('Segoe UI',9))
        if active:
            self.create_rectangle(9,184,196,194,fill='#393019',outline='')
            self.create_text(103,189,text=subtitle[:35] or 'RECOMMENDED',fill=GOLD,font=('Segoe UI',8,'bold'))
    @staticmethod
    def _wrap(v,width):
        words=str(v).split(); lines=['']
        for word in words:
            if len(lines[-1])+len(word)+1>width and lines[-1]:lines.append(word)
            else:lines[-1]=(lines[-1]+' '+word).strip()
        return lines


class AutoPickForge(LegacyUI):
    def __init__(self,root):
        self.run=RunState()
        self.ledger=[]
        self.last_drawn=None
        self.pending_action=None
        self.pending_new_signature=None
        self.pending_new_count=0
        self.initialized=False
        super().__init__(root)
        self.scanner=VisionScanner()
        enrich_profiles(self.profiles)
        self.load_profile(self.current_profile)
        self.root.title('Azeroth AutoPick — The Build Forge v2.1')
        self.root.geometry('1260x865')
        self.root.minsize(1050,745)
        self.initialized=True
        self.log('Build Forge v2.1 ready. Attach now discovers the actual game window; it cannot attach to this app.')

    def create_ui(self):
        self.root.configure(bg=BG)
        style=ttk.Style(self.root); style.theme_use('clam')
        style.configure('A.TNotebook',background=BG,borderwidth=0)
        style.configure('A.TNotebook.Tab',background='#241a12',foreground=GOLD,
                        padding=(20,10),font=('Georgia',11,'bold'),borderwidth=1)
        style.map('A.TNotebook.Tab',background=[('selected','#51351d')],
                  foreground=[('selected',CREAM)])
        style.configure('A.TCombobox',fieldbackground=DARK,background='#51351d',
                        foreground=CREAM,arrowcolor=GOLD,padding=5)
        style.configure('A.TScrollbar',background='#42301e')
        # Header
        header=tk.Frame(self.root,bg=BG,height=95)
        header.pack(fill='x',padx=22,pady=(12,3))
        RuneBadge(header).pack(side='left',padx=(0,15))
        ht=tk.Frame(header,bg=BG);ht.pack(side='left',fill='y')
        title_label(ht,'AZEROTH  AUTO PICK',size=25,color=GOLD).pack(anchor='w',pady=(4,0))
        txt_label(ht,'THE BUILD FORGE   •   INTELLIGENT CARD STRATEGY COMPANION',9,DIM_GOLD).pack(anchor='w')
        right=tk.Frame(header,bg=BG);right.pack(side='right',padx=8)
        self.status_var=tk.StringVar(value='DISCONNECTED')
        tk.Label(right,textvariable=self.status_var,bg='#282117',fg=GOLD,
                 font=('Segoe UI',10,'bold'),padx=13,pady=8).pack(anchor='e')
        txt_label(right,'LOCAL SCREEN RECOGNITION   ·   ZERO GOLD REROLLS',8).pack(anchor='e',pady=4)
        tk.Frame(self.root,bg='#926a35',height=2).pack(fill='x',padx=22,pady=(5,12))
        # Sidebar and notebook
        body=tk.Frame(self.root,bg=BG);body.pack(fill='both',expand=True,padx=20)
        left=panel(body,width=254);left.pack(side='left',fill='y',padx=(0,12))
        left.pack_propagate(False)
        title_label(left,'CLASS & BUILD',15).pack(anchor='w',padx=18,pady=(20,6))
        self.class_var=tk.StringVar(value=self.current_profile.split(' — ')[0] if ' — ' in self.current_profile else 'Paladin')
        self.class_grid=tk.Frame(left,bg=PANEL);self.class_grid.pack(fill='x',padx=13)
        for i,name in enumerate(SPELLS):
            b=tk.Button(self.class_grid,text=name,command=lambda x=name:self.select_class(x),
                        font=('Segoe UI',9,'bold'),bg='#33261a',fg=CREAM,
                        activebackground='#6d4b2c',activeforeground=GOLD,
                        relief='flat',padx=2,pady=4,cursor='hand2')
            b.grid(row=i//3,column=i%3,sticky='ew',padx=2,pady=2)
            self.class_grid.grid_columnconfigure(i%3,weight=1)
        txt_label(left,'ACTIVE STRATEGY',9,DIM_GOLD).pack(anchor='w',padx=18,pady=(18,4))
        self.profile_var=tk.StringVar(value=self.current_profile)
        self.profile_box=ttk.Combobox(left,textvariable=self.profile_var,
                                     state='readonly',width=28,style='A.TCombobox',values=list(self.profiles))
        self.profile_box.pack(fill='x',padx=14)
        self.profile_box.bind('<<ComboboxSelected>>',self.change_profile)
        styled_button(left,'SAVE BUILD',self.save).pack(fill='x',padx=14,pady=(11,4))
        styled_button(left,'DUPLICATE BUILD',self.duplicate_profile).pack(fill='x',padx=14,pady=4)
        tk.Frame(left,bg=BORDER,height=1).pack(fill='x',padx=14,pady=14)
        title_label(left,'RUN CONTROLS',14).pack(anchor='w',padx=18,pady=(0,10))
        styled_button(left,'ATTACH GAME   F8',self.attach,True).pack(fill='x',padx=14,pady=3)
        styled_button(left,'PREVIEW CHOICES   F7',self.preview).pack(fill='x',padx=14,pady=3)
        styled_button(left,'AUTO ON / OFF   F9',self.toggle,True).pack(fill='x',padx=14,pady=3)
        styled_button(left,'STOP NOW   F10',self.stop).pack(fill='x',padx=14,pady=3)
        self.tabs=ttk.Notebook(body,style='A.TNotebook')
        self.tabs.pack(side='left',fill='both',expand=True)
        self.dashboard_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.dashboard_tab,text='  COMMAND  ')
        self.build_dashboard()
        self.forge_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.forge_tab,text='  BUILD FORGE  ')
        self.build_forge()
        self.strategy_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.strategy_tab,text='  TACTICS  ')
        self.build_strategy()
        self.catalog_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.catalog_tab,text='  CODEX  ')
        self.build_catalog()
        self.ledger_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.ledger_tab,text='  RUN LEDGER  ')
        self.build_ledger()
        self.settings_tab=tk.Frame(self.tabs,bg=SHADE)
        self.tabs.add(self.settings_tab,text='  SYSTEM  ')
        self.build_settings()
        bottom=tk.Frame(self.root,bg=BG);bottom.pack(side='bottom',before=body,fill='x',padx=22,pady=(8,10))
        tk.Frame(bottom,bg=BORDER,height=1).pack(fill='x',pady=(0,7))
        tk.Label(bottom,text='EVENT CHRONICLE',fg=DIM_GOLD,bg=BG,font=('Georgia',10,'bold')).pack(anchor='w')
        self.logbox=tk.Text(bottom,height=4,relief='flat',bg=DARK,fg=CREAM,
                            insertbackground=GOLD,font=('Consolas',9),wrap='word',padx=9,pady=6)
        self.logbox.pack(fill='x')
        self.logbox.config(state='disabled')

    def build_dashboard(self):
        page=self.dashboard_tab
        hero=panel(page);hero.pack(fill='x',padx=15,pady=(16,11))
        title_label(hero,'THE CHOICE CHAMBER',20).pack(pady=(12,3))
        txt_label(hero,'Live recognised cards  •  rarity  •  priority  •  expected action',10).pack(pady=(0,12))
        row=tk.Frame(hero,bg=PANEL);row.pack(fill='x',padx=10,pady=(0,18))
        self.card_widgets=[]
        for i in range(4):
            card=ChoiceCard(row,i+1)
            if i<3:card.pack(side='left',expand=True,padx=4)
            self.card_widgets.append(card)
        self.card_row=row
        lower=tk.Frame(page,bg=SHADE);lower.pack(fill='both',expand=True,padx=15,pady=(0,12))
        left=panel(lower);left.pack(side='left',fill='both',expand=True,padx=(0,8))
        title_label(left,'STRATEGY VERDICT',15).pack(anchor='w',padx=16,pady=(14,7))
        self.decision_var=tk.StringVar(value='AWAITING A LEVEL-UP OR CACHE')
        tk.Label(left,textvariable=self.decision_var,bg=PANEL,fg=GOLD,
                 font=('Georgia',14,'bold'),wraplength=390,justify='left').pack(anchor='w',padx=16)
        self.reason_var=tk.StringVar(value='Attach to the game and preview the next three cards.')
        tk.Label(left,textvariable=self.reason_var,bg=PANEL,fg=CREAM,
                 font=('Segoe UI',10),wraplength=385,justify='left').pack(anchor='w',padx=16,pady=(10,10))
        self.recog_var=tk.StringVar(value='No screenshot analysed')
        txt_label(left,'LAYOUT & RECOGNITION',9,DIM_GOLD).pack(anchor='w',padx=16,pady=(18,3))
        tk.Label(left,textvariable=self.recog_var,bg=PANEL,fg=MUTED,font=('Segoe UI',9),wraplength=380,
                 justify='left').pack(anchor='w',padx=16,pady=(0,16))
        right=panel(lower,width=246);right.pack(side='left',fill='y');right.pack_propagate(False)
        title_label(right,'RUN TRACKER',15).pack(anchor='w',padx=16,pady=(14,8))
        txt_label(right,'Inferred from this app’s confirmed actions, not live game memory.',9,
                  wraplength=210,justify='left').pack(anchor='w',padx=16,pady=(0,8))
        self.run_stats_var=tk.StringVar(value='Picks 0   •   Rerolls 0\nSkips 0   •   Banishes 0')
        tk.Label(right,textvariable=self.run_stats_var,bg=PANEL,fg=CREAM,
                 justify='left',font=('Consolas',10)).pack(anchor='w',padx=16,pady=8)
        self.equipped_var=tk.StringVar(value='No picks confirmed yet')
        txt_label(right,'INFERRED EQUIPMENT',9,DIM_GOLD).pack(anchor='w',padx=16,pady=(12,4))
        tk.Label(right,textvariable=self.equipped_var,bg=PANEL,fg=CREAM,
                 justify='left',wraplength=212,font=('Segoe UI',9)).pack(anchor='w',padx=16)
        txt_label(right,'Reset and export from RUN LEDGER.',9,wraplength=200).pack(anchor='w',padx=15,pady=8)

    def _editor(self,parent,title,note):
        sub=tk.Frame(parent,bg=SHADE)
        nb=self.editor_tabs
        nb.add(sub,text=title)
        title_label(sub,title.upper(),15).pack(anchor='w',padx=14,pady=(15,5))
        txt_label(sub,note,10,wraplength=680,justify='left').pack(anchor='w',padx=14,pady=(0,10))
        t=tk.Text(sub,bg=DARK,fg=CREAM,insertbackground=GOLD,relief='flat',bd=0,
                  font=('Consolas',12),undo=True,padx=14,pady=12)
        t.pack(fill='both',expand=True,padx=14,pady=(0,14))
        return t

    def build_forge(self):
        area=self.forge_tab
        title_label(area,'THE BUILD FORGE',19).pack(anchor='w',padx=19,pady=(17,3))
        txt_label(area,'Twenty-seven editable builds. Priorities are ranked, and a matching card can upgrade an existing spell.',10).pack(anchor='w',padx=19,pady=(0,6))
        self.guide_var=tk.StringVar(value='Capstone & recommended race')
        tk.Label(area,textvariable=self.guide_var,bg=SHADE,fg=GOLD,font=('Segoe UI',10,'bold'),wraplength=740,justify='left').pack(anchor='w',padx=19,pady=(0,10))
        self.editor_tabs=ttk.Notebook(area,style='A.TNotebook')
        self.editor_tabs.pack(fill='both',expand=True,padx=17,pady=(0,15))
        self.level_tab=self._editor(area,'SPELL PRIORITY','Six planned spells in ranked order. Your highest-priority active should appear first.')
        self.passive_tab=self._editor(area,'PASSIVES','Optional shared passive-name priorities (community rebuild labels; only selected when visible in your version).')
        self.loot_tab=self._editor(area,'JEWELLERY','Ordered rings, trinkets, and amulets. Existing equipment is protected from accidental replacement.')
        self.avoid_tab=self._editor(area,'NEVER PICK','Cards listed here will never be chosen, regardless of rarity.')
        self.banish_tab=self._editor(area,'BANISH','Jewellery names you explicitly want banished; only after rejecting all good choices.')

    def build_strategy(self):
        area=self.strategy_tab
        canvas=tk.Canvas(area,bg=SHADE,highlightthickness=0)
        scrollbar=ttk.Scrollbar(area,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        frame=tk.Frame(canvas,bg=SHADE)
        holder=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfig(holder,width=e.width))
        title_label(frame,'THE TACTICIAN',20).pack(anchor='w',padx=20,pady=(19,3))
        txt_label(frame,'Separate rarity rules, slot protection, reserve rerolls and conservative actions.',10).pack(anchor='w',padx=20,pady=(0,14))
        section=panel(frame);section.pack(fill='x',padx=16,pady=8)
        title_label(section,'CARD QUALITY',13).pack(anchor='w',padx=15,pady=(13,9))
        for label,key,default in [('Level-up minimum','min_rarity_level','Rare'),
                                  ('Jewellery minimum','min_rarity_loot','Rare'),
                                  ('New spell minimum','min_new_rarity','Uncommon'),
                                  ('Spell upgrade minimum','min_upgrade_rarity','Uncommon')]:
            row=tk.Frame(section,bg=PANEL);row.pack(fill='x',padx=15,pady=5)
            txt_label(row,label,10,CREAM).pack(side='left')
            value=tk.StringVar(value=self.settings.get(key,default))
            setattr(self, {'min_rarity_level':'min_rarity_level_var',
                            'min_rarity_loot':'min_rarity_loot_var',
                            'min_new_rarity':'new_floor_var',
                            'min_upgrade_rarity':'upgrade_floor_var'}[key],value)
            ttk.Combobox(row,textvariable=value,values=list(RARITIES),state='readonly',
                         width=14,style='A.TCombobox').pack(side='right')
        txt_label(section,'Legendary cards scale at 3.2× Common, but a Legendary off-build item can still be worse than an on-build Rare.',9,
                  wraplength=640,justify='left').pack(anchor='w',padx=15,pady=(5,12))
        opts=panel(frame);opts.pack(fill='x',padx=16,pady=8)
        title_label(opts,'SMART SAFETY RULES',13).pack(anchor='w',padx=15,pady=(13,8))
        self.free_var=tk.BooleanVar(value=self.settings.get('auto_free_reroll',self.settings.get('use_free_rerolls',True)))
        self.skip_var=tk.BooleanVar(value=self.settings.get('auto_skip',True))
        self.banish_var=tk.BooleanVar(value=self.settings.get('auto_banish',self.settings.get('auto_banish_jewelry',True)))
        self.amulet_var=tk.BooleanVar(value=self.settings.get('protect_amulet',True))
        self.jewelry_var=tk.BooleanVar(value=self.settings.get('protect_jewelry',True))
        self.adaptive_var=tk.BooleanVar(value=self.settings.get('adaptive_rarity',False))
        self.core_var=tk.BooleanVar(value=self.settings.get('prefer_core_upgrades',True))
        self.passives_var=tk.BooleanVar(value=self.settings.get('accept_passives',True))
        for label,var in [
            ('Use free rerolls only; never pay gold',self.free_var),
            ('Skip if the reroll explicitly costs gold',self.skip_var),
            ('Use explicit jewellery banish list (only when no good pick exists)',self.banish_var),
            ('Protect a selected amulet from being replaced',self.amulet_var),
            ('Protect occupied ring/trinket slots from replacements',self.jewelry_var),
            ('Allow lower-rarity CORE upgrades after all free rerolls are used',self.adaptive_var),
            ('Prioritise existing core spell rank-ups',self.core_var),
            ('Recognise configured passive names',self.passives_var)]:
            tk.Checkbutton(opts,text=label,variable=var,bg=PANEL,fg=CREAM,
                           activebackground=PANEL,activeforeground=GOLD,selectcolor=DARK,
                           font=('Segoe UI',10),anchor='w').pack(fill='x',padx=15,pady=3)
        sliders=panel(frame);sliders.pack(fill='x',padx=16,pady=8)
        title_label(sliders,'RESOURCE CONTROL',13).pack(anchor='w',padx=15,pady=(11,7))
        self.reserve_var=tk.IntVar(value=int(self.settings.get('max_rerolls_reserved',0)))
        self.max_banish_var=tk.IntVar(value=int(self.settings.get('max_banish_per_run',2)))
        self.rarity_weight_var=tk.DoubleVar(value=float(self.settings.get('rarity_weight',1)))
        for title,var,frm,to,res in [('Reserve this many free rerolls',self.reserve_var,0,4,1),
                                     ('Maximum banishes per run',self.max_banish_var,0,3,1),
                                     ('Rarity weight vs preference order',self.rarity_weight_var,0,2,.25)]:
            txt_label(sliders,title,10,CREAM).pack(anchor='w',padx=15)
            tk.Scale(sliders,variable=var,from_=frm,to=to,resolution=res,orient='horizontal',
                     bg=PANEL,fg=CREAM,troughcolor=DARK,highlightthickness=0,
                     length=370).pack(anchor='w',padx=15,pady=(0,7))
        styled_button(frame,'SAVE TACTICS',self.save,True).pack(anchor='w',padx=16,pady=(5,20))

    def build_catalog(self):
        area=self.catalog_tab
        title_label(area,'CODEX OF POWER',20).pack(anchor='w',padx=18,pady=(17,5))
        txt_label(area,'Community-sourced spell names and in-run jewellery. This is a reference catalogue, not hidden game data.',10,
                  wraplength=740,justify='left').pack(anchor='w',padx=18,pady=(0,10))
        row=tk.Frame(area,bg=SHADE);row.pack(fill='x',padx=17,pady=4)
        self.catalog_class=tk.StringVar(value='Paladin')
        ttk.Combobox(row,textvariable=self.catalog_class,values=list(SPELLS),state='readonly',
                     width=18,style='A.TCombobox').pack(side='left')
        styled_button(row,'SHOW CLASS',self.show_catalog).pack(side='left',padx=8)
        self.catalog_text=tk.Text(area,bg=DARK,fg=CREAM,relief='flat',font=('Consolas',10),
                                  wrap='word',padx=15,pady=14)
        self.catalog_text.pack(fill='both',expand=True,padx=17,pady=(9,15))
        self.show_catalog()

    def show_catalog(self):
        klass=self.catalog_class.get()
        sections=[f'CLASS SPELLS   /   {klass.upper()}', *[f'  {i:02d}    {s}' for i,s in enumerate(SPELLS[klass],1)],
                  '\nPASSIVE LABELS (COMMUNITY REBUILD; CHECK LIVE GAME)',
                  *[f'  {name:<33} {meta[0]}' for name,meta in PASSIVES.items()],
                  '\nRINGS', *['  '+n for n in RINGS],
                  '\nTRINKETS', *['  '+n for n in TRINKETS],
                  '\nGENERAL AMULETS',*['  '+n for n in AMULETS],
                  '\nNAMED LEGENDARY SPELL AMULET FAMILIES',*['  '+n for n in LEGENDARY_AMULETS],
                  '\nCLASS SPELL → LEGENDARY AMULET FAMILY (variant must be verified in-game)',
                  *[f"  {s:<26} {a or '—'}" for s,a in SPELL_AMULETS[klass].items()]]
        self.catalog_text.config(state='normal')
        self.catalog_text.delete('1.0','end');self.catalog_text.insert('1.0','\n'.join(sections))
        self.catalog_text.config(state='disabled')

    def build_ledger(self):
        area=self.ledger_tab
        title_label(area,'RUN CHRONICLE',20).pack(anchor='w',padx=18,pady=(17,4))
        txt_label(area,'Only confirmed inputs made through AutoPick are recorded. Manual game choices are not observable.',10,
                  wraplength=750,justify='left').pack(anchor='w',padx=18,pady=(0,12))
        bar=tk.Frame(area,bg=SHADE);bar.pack(fill='x',padx=16,pady=7)
        styled_button(bar,'EXPORT CSV',self.export_csv,True).pack(side='left',padx=2)
        styled_button(bar,'RESET RUN',self.new_run).pack(side='left',padx=7)
        self.ledger_text=tk.Text(area,bg=DARK,fg=CREAM,relief='flat',
                                 font=('Consolas',11),wrap='word',padx=15,pady=12)
        self.ledger_text.pack(fill='both',expand=True,padx=16,pady=(5,15))
        self.ledger_text.config(state='disabled')

    def build_settings(self):
        area=self.settings_tab
        title_label(area,'SYSTEM & SAFEGUARDS',20).pack(anchor='w',padx=18,pady=(17,5))
        for heading,desc in [
            ('AUTOMATIC LAYOUT','Detects card borders from every popup. No manual calibration or saved coordinates.'),
            ('INPUT SAFETY','Only inputs to your attached foreground game window. F10 stops immediately.'),
            ('STRICT GOLD RULE','Never presses R if gold costs are detected or ambiguous. Paid rerolls cannot be enabled.'),
            ('INFERRED RUN STATE','Jewellery and spell choices are tracked from this app’s successful inputs, not read from your game save.'),
            ('COMMUNITY DATA','Spell lists are from ASBuilder. Build strengths and passive labels are editable recommendations.'),
        ]:
            p=panel(area);p.pack(fill='x',padx=16,pady=6)
            title_label(p,heading,11).pack(anchor='w',padx=15,pady=(10,4))
            txt_label(p,desc,10,wraplength=670,justify='left').pack(anchor='w',padx=15,pady=(0,12))
        opts=tk.Frame(area,bg=SHADE);opts.pack(fill='x',padx=18,pady=(12,6))
        txt_label(opts,'CARD INPUT',10,CREAM).pack(side='left')
        self.input_var=tk.StringVar(value=self.settings.get('input_mode','number'))
        ttk.Combobox(opts,textvariable=self.input_var,values=['number','click'],
                     state='readonly',width=12,style='A.TCombobox').pack(side='left',padx=10)
        txt_label(opts,'OCR MATCH FLOOR',10,CREAM).pack(side='left',padx=(20,2))
        self.threshold_var=tk.DoubleVar(value=float(self.settings.get('min_confidence',.88)))
        tk.Scale(opts,from_=.80,to=.98,resolution=.01,variable=self.threshold_var,
                 bg=SHADE,fg=CREAM,orient='horizontal',troughcolor=DARK,
                 highlightthickness=0,length=165).pack(side='left')
        self.count_var=tk.StringVar(value='3 / 4 auto')
        styled_button(area,'SAVE SYSTEM SETTINGS',self.save,True).pack(anchor='w',padx=18,pady=(12,18))

    def select_class(self,klass):
        self.store_profile()
        matching=[k for k,v in self.profiles.items() if v.get('class')==klass]
        if not matching:return
        self.current_profile=matching[0]
        self.profile_var.set(self.current_profile)
        self.load_profile(self.current_profile)
        self.log('Class changed to '+klass+'. Auto input paused until rearmed.')
        self.armed=False;self.status();self.save()

    def store_profile(self):
        if not hasattr(self,'level_tab'):return
        super().store_profile()
        self.profiles[self.current_profile]['passives']=parse_names(self.passive_tab.get('1.0','end'))

    def load_profile(self,name):
        super().load_profile(name)
        prof=self.profiles.get(name,{})
        self.passive_tab.delete('1.0','end')
        self.passive_tab.insert('1.0','\n'.join(prof.get('passives') or make_passive_plan(prof.get('style',''),prof.get('class',''))))
        if hasattr(self,'class_var'):
            self.class_var.set(prof.get('class','CUSTOM'))
        if hasattr(self,'guide_var'):
            self.guide_var.set('Suggested talent capstone: '+prof.get('capstone','User choice')+'    •    Suggested race: '+prof.get('race','Any')+'\n'+prof.get('description',''))

    def save(self):
        if not hasattr(self,'input_var'):return
        # Preserve backward-compatible settings, then apply v2 controls.
        super().save()
        self.settings.update({
            'min_spell_rarity':self.min_rarity_level_var.get(),
            'min_loot_rarity':self.min_rarity_loot_var.get(),
            'min_new_rarity':self.new_floor_var.get(),
            'min_upgrade_rarity':self.upgrade_floor_var.get(),
            'adaptive_rarity':self.adaptive_var.get(),
            'prefer_core_upgrades':self.core_var.get(),
            'max_rerolls_reserved':int(self.reserve_var.get()),
            'auto_banish':self.banish_var.get(),
            'max_banish_per_run':int(self.max_banish_var.get()),
            'auto_skip':self.skip_var.get(),
            'auto_free_reroll':self.free_var.get(),
            'protect_amulet':self.amulet_var.get(),
            'protect_jewelry':self.jewelry_var.get(),
            'accept_passives':self.passives_var.get(),
            'min_confidence':float(self.threshold_var.get()),
            'rarity_weight':float(self.rarity_weight_var.get()),
        })
        try:
            save_json(BASE/'settings.json',self.settings)
            save_json(BASE/'profiles.json',self.profiles)
        except OSError as exc:self.log('Save failed: '+str(exc))

    def log(self,message):
        if hasattr(self,'logbox'):
            super().log(message)

    def status(self):
        super().status()

    def attach(self):
        """F8 on game OR clicking Attach inside the app both work correctly.

        Clicking inside this Tk window makes IT the foreground window. v2.0
        incorrectly attached to the Tk window because its title had 'Azeroth'.
        Always check process+title and enumerate actual game windows instead.
        """
        current=inspect_window(foreground_window())
        if current and current.score >= 60:
            self._attach_real_game(current)
            return
        candidates=discover_game_windows()
        winner=choose_unambiguous(candidates)
        if winner:
            self._attach_real_game(winner)
        elif candidates:
            self._show_game_picker(candidates)
        else:
            self.log('GAME NOT FOUND: Open Azeroth Survivors (not AutoPick), click into it, and press F8. The app will never attach to itself.')
            messagebox.showinfo('Game window not found',
                'AutoPick could not identify a separate Azeroth Survivors game window.\n\n'
                'Open the game, click directly inside the game, and press F8 on your keyboard.\n'
                'Do not choose the AutoPick window. If the game is in a browser, make sure the browser tab has the game title.',
                parent=self.root)

    def _attach_real_game(self, candidate:GameWindow):
        fresh=inspect_window(candidate.hwnd)
        if fresh is None or fresh.score < 60:
            self.log('Attach blocked: selected window is not a verified game window.')
            return
        self.armed=False
        super().attach(fresh.hwnd)
        self.new_run(quiet=True)
        self.scanner.invalidate()
        self.last_drawn=None
        self.decision_var.set('CONNECTED — WAITING FOR CHOICE SCREEN')
        self.reason_var.set('Start a run. Switch focus back to Azeroth Survivors. F7 previews a choice; F9 enables automatic input.')
        self.recog_var.set('Attached window: '+fresh.title+'   •   OCR has not scanned cards yet')
        self.status()
        self.log('Game verified: '+fresh.title+'  ['+fresh.process.rsplit('\\',1)[-1]+']')
        self.log('Ready: F9 arms AutoPick; switch focus to the game for live scanning. F10 stops immediately.')

    def _show_game_picker(self,candidates:list[GameWindow]):
        """Never guess which of several live game windows should receive input."""
        self.armed=False;self.status()
        win=tk.Toplevel(self.root)
        win.title('Choose Azeroth Survivors window')
        win.configure(bg=PANEL)
        win.geometry('640x285')
        win.transient(self.root)
        title_label(win,'CHOOSE THE GAME WINDOW',16).pack(padx=20,pady=(15,5),anchor='w')
        txt_label(win,'More than one matching window is open. Select the actual game, not AutoPick.',10).pack(padx=20,anchor='w')
        box=tk.Listbox(win,bg=DARK,fg=CREAM,selectbackground='#725026',
                       selectforeground=CREAM,highlightthickness=1,
                       font=('Consolas',10),height=6)
        box.pack(fill='both',expand=True,padx=20,pady=12)
        for candidate in candidates:
            label=f'{candidate.title[:55]}   [{candidate.process.rsplit(chr(92),1)[-1]}]'
            box.insert('end',label)
        box.selection_set(0)
        row=tk.Frame(win,bg=PANEL);row.pack(fill='x',padx=20,pady=(0,14))
        def accept():
            picked=box.curselection()
            if not picked:return
            candidate=candidates[picked[0]]
            win.destroy()
            self._attach_real_game(candidate)
        styled_button(row,'ATTACH SELECTED GAME',accept,True).pack(side='left')
        styled_button(row,'CANCEL',win.destroy).pack(side='right')
        box.bind('<Double-Button-1>',lambda e:accept())
        win.grab_set()

    def new_run(self,quiet=False):
        if not quiet and self.armed:self.stop()
        self.run.reset();self.pending_action=None;self.pending_new_signature=None;self.pending_new_count=0;self.last_drawn=None
        self.last_picked=None;self.last_seen=None;self.used_banish_targets.clear()
        if hasattr(self,'scanner') and hasattr(self.scanner,'invalidate'):self.scanner.invalidate()
        self._update_tracker()
        if not quiet:self.log('Run state reset. This clears inferred inventory and banish history.')

    def _update_tracker(self):
        self.run_stats_var.set(f'Picks {self.run.picks}   •   Rerolls {self.run.rerolls}\nSkips {self.run.skips}   •   Banishes {self.run.banishes}')
        equip=self.run.equipped_rings+self.run.equipped_trinkets
        if self.run.equipped_amulet:equip.append('Amulet: '+self.run.equipped_amulet)
        self.equipped_var.set('\n'.join('• '+s for s in equip) if equip else 'No confirmed jewellery selections')

    def export_csv(self):
        from tkinter import filedialog
        path=filedialog.asksaveasfilename(title='Export run ledger',defaultextension='.csv',
                                          filetypes=[('CSV','*.csv')],parent=self.root)
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as file:
                writer=csv.writer(file);writer.writerow(['time','kind','action','card','label','reason','profile'])
                for e in self.ledger:writer.writerow(e)
            self.log('Run ledger exported.')
        except OSError as e:self.log('Export failed: '+str(e))

    def _record_action(self,action,kind):
        self.run.remember(action,kind,self.profiles[self.current_profile].get('class',''))
        item=(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),kind,action.kind,action.index,
              action.label,action.reason,self.current_profile)
        self.ledger.append(item)
        self.ledger_text.config(state='normal')
        self.ledger_text.insert('end',f'[{item[0]}]  {item[2].upper():7}  {item[4] or action.reason}\n')
        self.ledger_text.see('end');self.ledger_text.config(state='disabled')
        self._update_tracker()

    def hotkeys(self):
        try:
            actions={0x77:self.attach,0x76:self.preview,0x78:self.toggle,0x79:self.stop}
            for vk,fun in actions.items():
                down=key_down(vk)
                if down and not self.prev_keys.get(vk,False):fun()
                self.prev_keys[vk]=down
        except Exception as e:self.log('Hotkey: '+str(e))
        self.root.after(90,self.hotkeys)

    def submit(self,preview=False):
        if not self.target or (self.job and not self.job.done()):return
        if not preview and foreground_window()!=self.target:return
        self.store_profile()
        cfg=copy.deepcopy(self.settings)
        cfg.update({'min_spell_rarity':self.min_rarity_level_var.get(),
                    'min_loot_rarity':self.min_rarity_loot_var.get(),
                    'min_new_rarity':self.new_floor_var.get(),
                    'min_upgrade_rarity':self.upgrade_floor_var.get(),
                    'adaptive_rarity':self.adaptive_var.get(),
                    'prefer_core_upgrades':self.core_var.get(),
                    'max_rerolls_reserved':int(self.reserve_var.get()),
                    'max_banish_per_run':int(self.max_banish_var.get()),
                    'auto_banish':self.banish_var.get(),
                    'auto_skip':self.skip_var.get(),
                    'auto_free_reroll':self.free_var.get(),
                    'protect_amulet':self.amulet_var.get(),
                    'protect_jewelry':self.jewelry_var.get(),
                    'accept_passives':self.passives_var.get(),
                    'min_confidence':float(self.threshold_var.get()),
                    'rarity_weight':float(self.rarity_weight_var.get())})
        profile=copy.deepcopy(self.profiles[self.current_profile])
        run=copy.deepcopy(self.run)
        self.preview_job=preview
        self.job=self.executor.submit(self.scanner.scan,self.target,cfg,profile,run)

    def loop(self):
        if self.job and self.job.done():
            try:
                result=self.job.result()
                self.handle_result(result,self.preview_job)
            except Exception as e:
                self.armed=False;self.status();self.log('OCR stopped: '+str(e))
            finally:self.job=None
        if self.armed and not self.job and self.target and foreground_window()==self.target:
            self.submit(False)
        # Make the armed-vs-active distinction visible without generating logs.
        focused=bool(self.target and foreground_window()==self.target)
        if focused!=getattr(self,'_was_game_foreground',None):
            self._was_game_foreground=focused
            self.status()
        self.root.after(100,self.loop)

    def preview(self):
        if not self.target:self.log('Attach the game first (F8 or the Attach button).');return
        if foreground_window()==self.target:
            self.submit(True)
        else:
            # Window is behind our GUI. Temporarily hide the GUI for OCR.
            # Do NOT restore after an arbitrary 500ms: slow initial OCR would
            # end up capturing AutoPick instead of the game itself.
            if self.job and not self.job.done():
                self.log('Preview already running; try again after the current scan.')
                return
            self.root.withdraw()
            self.root.after(350,self._preview_hidden)

    def _preview_hidden(self):
        self.submit(True)
        self.root.after(110,self._restore_after_preview)

    def _restore_after_preview(self):
        if self.job and not self.job.done():
            self.root.after(110,self._restore_after_preview)
            return
        self.root.deiconify()

    def handle_result(self,result,preview):
        display_key=(result.signature,result.kind,result.header,result.layout_source,result.decision.reason)
        if display_key!=self.last_drawn:
            self.last_drawn=display_key
            if len(result.cards)>3 and not self.card_widgets[3].winfo_manager():
                self.card_widgets[3].pack(side='left',expand=True,padx=3)
            elif len(result.cards)<=3 and self.card_widgets[3].winfo_manager():
                self.card_widgets[3].pack_forget()
            action=result.decision
            self.decision_var.set(f'{action.kind.upper()}  {action.label}'.strip() if result.kind else 'WATCHING FOR CHOICE CARDS')
            self.reason_var.set(action.reason or '—')
            self.recog_var.set(f'{result.layout_source}   •   '+
                               ('verified geometry' if result.is_verified else 'unverified geometry')+
                               (f'   •   class: {result.inferred_class}' if result.inferred_class else ''))
            for i,widget in enumerate(self.card_widgets):
                if i<len(result.cards):
                    c=result.cards[i]
                    rarity=result.rarities[i] if i<len(result.rarities) else '?'
                    ignored={'common','uncommon','rare','epic','legendary','new spell','new'}
                    names=[x for x in c if clean(x) not in ignored and 'rank' not in clean(x)]
                    name=names[0] if names else '?'
                    widget.render(name,rarity,' / '.join(c[-2:]),
                                  action.kind=='pick' and action.index==i+1,
                                  'STRATEGY MATCH' if action.index==i+1 else '')
                else:widget.render('—','?','No card',False,'')
        if preview:
            self.log(f'PREVIEW {result.kind or "unknown"}: '+
                     ' | '.join('/'.join(row[:4]) for row in result.cards))
            self.log(f'NEXT: {result.decision.kind} {result.decision.label} — {result.decision.reason}')
            self.log(f'BUTTONS reroll={result.controls.reroll_text!r}, skip={result.controls.skip_text!r}')
            return
        if not self.armed or foreground_window()!=self.target:return
        # Pending input is acknowledged only after the game changes its cards
        # or dismisses the choice screen. Never press another key blindly.
        if self.pending_action:
            oldsig,action,kind,sent=self.pending_action
            if result.signature!=oldsig:
                if result.signature==self.pending_new_signature:
                    self.pending_new_count+=1
                else:
                    self.pending_new_signature=result.signature
                    self.pending_new_count=1
                # Require the changed state to persist across two frames;
                # brief flashes should never be mistaken for a confirmed pick.
                if self.pending_new_count>=2:
                    self._record_action(action,kind)
                    self.pending_action=None
                    self.pending_new_signature=None;self.pending_new_count=0
                    self.last_seen=None;self.streak=0
                    self.scanner.invalidate()
                    self.log('CONFIRMED '+action.kind.upper()+' '+(action.label or action.reason))
                return
            self.pending_new_signature=None;self.pending_new_count=0
            if time.monotonic()-sent>4.2:
                self.stop();self.log('Safety stop: screen did not change after action.')
            return
        if not result.kind or not result.signature:
            self.streak=0;self.last_seen=None
            return
        selected=self.profiles[self.current_profile].get('class','')
        if result.inferred_class and selected and result.inferred_class!=selected:
            self.stop();self.log(f'Class mismatch: screen suggests {result.inferred_class}; profile is {selected}. Switch build.')
            return
        if not result.is_verified:
            self.stop();self.log('Unverified choice geometry: no input sent.')
            return
        sig=result.signature
        if sig==self.last_seen:self.streak+=1
        else:self.last_seen=sig;self.streak=1
        if self.streak<2:return
        action=result.decision
        if action.kind=='wait':
            if sig!=self.last_picked:
                self.log('WAIT '+action.reason)
                self.last_picked=sig
            return
        if time.monotonic()-self.last_action<.23:return
        try:
            if foreground_window()!=self.target:return
            import pyautogui
            if action.kind=='pick':
                if self.input_var.get()=='click':
                    from autopick.capture import capture_window
                    shot=capture_window(self.target)
                    box=result.layout.cards[action.index-1]
                    pyautogui.click(shot.left+box.cx,shot.top+box.cy,_pause=False)
                else:pyautogui.press(str(action.index),_pause=False)
            elif action.kind=='reroll':
                if result.free_reroll_guard!='free-looking':
                    self.log('Reroll blocked: no verified gold-free button.');return
                pyautogui.press('r',_pause=False)
            elif action.kind=='skip':pyautogui.press('x',_pause=False)
            elif action.kind=='banish':
                if not result.banish_points or not result.banish_points[action.index-1]:
                    self.log('Banish blocked: button not located.');return
                from autopick.capture import capture_window
                shot=capture_window(self.target)
                point=result.banish_points[action.index-1]
                pyautogui.click(shot.left+point[0],shot.top+point[1],_pause=False)
            else:return
            self.last_action=time.monotonic()
            self.pending_action=(sig,action,result.kind,self.last_action)
            self.pending_new_signature=None;self.pending_new_count=0
            self.log('SENT '+action.kind.upper()+' '+(action.label or action.reason))
        except Exception as exc:
            self.stop();self.log('Input error: '+str(exc))

    def status(self):
        if not self.target:
            self.status_var.set('NOT CONNECTED  •  CLICK ATTACH GAME')
        elif self.armed and foreground_window()!=self.target:
            self.status_var.set('AUTO ARMED  •  CLICK GAME TO ACT')
        elif self.armed:
            self.status_var.set('AUTO ACTIVE  •  '+title_of(self.target)[:32])
        else:
            self.status_var.set('CONNECTED  •  PREVIEW ONLY  •  '+title_of(self.target)[:25])

    def toggle(self):
        if not self.target:
            self.log('Attach the actual game first (F8 or ATTACH GAME).')
            return
        selected=inspect_window(self.target)
        if not selected or selected.score<60:
            self.armed=False;self.status()
            self.log('AUTO BLOCKED: attached HWND is missing or is not the game. Attach the real game again.')
            return
        self.save()
        self.armed=not self.armed
        self.pending_action=None
        self.pending_new_signature=None;self.pending_new_count=0
        self.last_seen=None;self.streak=0;self.last_picked=None
        self.status()
        if self.armed:
            self.log('AUTO ARMED: click the game window to begin. Input only occurs while that game is in front.')
        else:
            self.log('AUTO INPUT PAUSED.')

    def stop(self):
        self.armed=False
        self.pending_action=None
        self.status()
        self.log('STOP — no automatic inputs.')

    def close(self):
        try:self.save()
        finally:
            self.armed=False
            self.executor.shutdown(wait=False,cancel_futures=True)
            self.root.destroy()


def main():
    if sys.platform!='win32':
        print('The control application requires Windows 10/11.')
        raise SystemExit(1)
    try:ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:ctypes.windll.user32.SetProcessDPIAware()
        except Exception:pass
    root=tk.Tk()
    AutoPickForge(root)
    root.mainloop()

if __name__=='__main__':main()

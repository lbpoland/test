"""Small GUI lifecycle base: profile persistence, hotkeys and focus safety.

The Build Forge entry point supplies all UI and decision logic. Keeping this
base separate makes it easy to test and change the engine without a legacy GUI.
"""
from __future__ import annotations
import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import messagebox, simpledialog

from .catalog import make_profiles
from .capture import foreground_window, title_of

ROOT=Path(__file__).resolve().parent.parent
SETTINGS=ROOT/'settings.json'
PROFILES=ROOT/'profiles.json'
DEFAULT_SETTINGS={
    'profile':'Paladin — Consecration AoE','input_mode':'number',
    'min_confidence':.88,'min_rarity_level':'Rare','min_rarity_loot':'Rare',
    'use_free_rerolls':True,'auto_skip':True,'auto_banish_jewelry':True,
    'rarity_weight':1.0,'auto_free_reroll':True,
    'min_spell_rarity':'Rare','min_loot_rarity':'Rare',
    'min_new_rarity':'Rare','min_upgrade_rarity':'Rare',
    'adaptive_rarity':False,'prefer_core_upgrades':True,
    'max_rerolls_reserved':0,'auto_banish':True,'max_banish_per_run':2,
    'protect_amulet':True,'protect_jewelry':True,'accept_passives':True,
}


def load_json(path:Path,default:dict)->dict:
    try:
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            if isinstance(value,dict):return value
    except (OSError,ValueError):pass
    return copy.deepcopy(default)


def save_json(path:Path,value:dict)->None:
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    tmp.replace(path)


class AutoPickBase:
    def __init__(self,root):
        self.root=root
        self.settings={**DEFAULT_SETTINGS,**load_json(SETTINGS,{})}
        self.profiles=load_json(PROFILES,{})
        for key,plan in make_profiles().items():self.profiles.setdefault(key,plan)
        self.current_profile=self.settings.get('profile',DEFAULT_SETTINGS['profile'])
        if self.current_profile not in self.profiles:
            self.current_profile=next(iter(self.profiles))
        self.target=0
        self.armed=False
        self.job=None
        self.preview_job=False
        self.executor=ThreadPoolExecutor(max_workers=1)
        self.last_seen=None
        self.streak=0
        self.last_picked=None
        self.last_action=0.
        self.used_banish_targets=set()
        self.prev_keys={}
        self.create_ui()
        self.load_profile(self.current_profile)
        self.log('Ready. F8 attach; F7 preview; F9 auto; F10 stop.')
        self.root.after(95,self.hotkeys)
        self.root.after(160,self.loop)
        self.root.protocol('WM_DELETE_WINDOW',self.close)

    def store_profile(self):
        if not hasattr(self,'level_tab'):return
        from .engine import parse_names
        old=self.profiles.get(self.current_profile,{})
        new={**old}
        for attr,key in (('level_tab','level'),('loot_tab','loot'),
                         ('avoid_tab','avoid'),('banish_tab','banish_loot')):
            new[key]=parse_names(getattr(self,attr).get('1.0','end'))
        self.profiles[self.current_profile]=new

    def load_profile(self,name):
        prof=self.profiles.get(name,{})
        for attr,key in (('level_tab','level'),('loot_tab','loot'),
                         ('avoid_tab','avoid'),('banish_tab','banish_loot')):
            widget=getattr(self,attr)
            widget.delete('1.0','end')
            widget.insert('1.0','\n'.join(prof.get(key,[])))

    def change_profile(self,event=None):
        self.store_profile()
        chosen=self.profile_var.get()
        if chosen not in self.profiles:return
        self.current_profile=chosen
        self.load_profile(chosen)
        self.armed=False;self.status()
        self.save()
        self.log('Loaded build: '+chosen+'. Automatic input paused.')

    def duplicate_profile(self):
        self.store_profile()
        name=simpledialog.askstring('Duplicate strategy','New build name:',parent=self.root)
        if not name or not name.strip():return
        name=name.strip()
        if name in self.profiles:
            messagebox.showwarning('Existing name','That build already exists.',parent=self.root)
            return
        self.profiles[name]=copy.deepcopy(self.profiles[self.current_profile])
        self.current_profile=name
        self.profile_var.set(name)
        self.profile_box.configure(values=list(self.profiles))
        self.load_profile(name)
        self.save()
        self.log('New custom build: '+name)

    def save(self):
        self.store_profile()
        self.settings.update({
            'profile':self.current_profile,'input_mode':self.input_var.get(),
            'min_confidence':float(self.threshold_var.get()),
            'min_rarity_level':self.min_rarity_level_var.get(),
            'min_rarity_loot':self.min_rarity_loot_var.get(),
            'use_free_rerolls':bool(self.free_var.get()),
            'auto_skip':bool(self.skip_var.get()),
            'auto_banish_jewelry':bool(self.banish_var.get()),
            'rarity_weight':float(self.rarity_weight_var.get()),
        })
        save_json(PROFILES,self.profiles)
        save_json(SETTINGS,self.settings)
        self.log('Build and configuration saved.')

    def attach(self, hwnd=None):
        # v2.1: the caller resolves the real game window before attaching.
        # A GUI button click must not silently target AutoPick's own HWND.
        hwnd=foreground_window() if hwnd is None else hwnd
        if not hwnd:
            self.log('No foreground game window. Focus the game and press F8.')
            return
        self.target=hwnd
        self.armed=False
        self.last_seen=None;self.last_picked=None;self.streak=0
        self.used_banish_targets.clear()
        self.status()
        self.log('Attached: '+title_of(hwnd)+'. Automatic input remains OFF.')

    def status(self):
        s=('NOT ATTACHED' if not self.target else
           ('AUTO ON' if self.armed else 'PREVIEW ONLY')+'  ·  '+title_of(self.target)[:38])
        self.status_var.set(s)

    def log(self,message):
        if not hasattr(self,'logbox'):return
        self.logbox.config(state='normal')
        self.logbox.insert('end','['+time.strftime('%H:%M:%S')+'] '+message+'\n')
        self.logbox.see('end')
        self.logbox.config(state='disabled')

    # The Build Forge implements the runtime methods below. These placeholders
    # are not called in production and make architectural dependencies explicit.
    def create_ui(self):raise NotImplementedError
    def hotkeys(self):raise NotImplementedError
    def loop(self):raise NotImplementedError
    def close(self):raise NotImplementedError

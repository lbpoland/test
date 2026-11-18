"""Identify the *game* Windows window, never the AutoPick GUI.

The original v2.0 attach button used GetForegroundWindow(), which returned
AutoPick's own window when clicked. This module enumerates visible top-level
windows and uses the process image + title to find an unambiguous game window.
No process memory is read, injected or modified.
"""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
import ctypes.wintypes
import os
from pathlib import PureWindowsPath


@dataclass(frozen=True)
class GameWindow:
    hwnd: int
    title: str
    process: str
    pid: int
    score: int


SELF_MARKERS = ("azeroth autopick", "azeroth auto pick", "the build forge", "build forge v2")


def game_score(title: str, process: str = "", own_process: bool = False) -> int:
    """Classify based on ordinary OS window metadata, not contents/memory.

    The program title includes the words 'Azeroth', but must never match.
    Browser windows must have an actual game-specific tab title to qualify
    for background automatic discovery.
    """
    t = (title or "").casefold()
    p = PureWindowsPath((process or "").replace("/", "\\")).name.casefold()
    compact_title = ''.join(c for c in t if c.isalnum())
    compact_proc = ''.join(c for c in p if c.isalnum())
    if own_process or any(marker in t for marker in SELF_MARKERS):
        return -1
    if 'azerothsurvivors' in compact_proc:
        return 130
    if 'azerothsurvivors' in compact_title:
        return 115
    if p in ('wow.exe', 'wow64.exe', 'worldofwarcraft.exe'):
        return 87
    if 'world of warcraft' in t:
        return 70
    return 0


def is_browsable_game_window(title: str, process: str) -> bool:
    """Positive identification for game tab; generic browsers are never guessed."""
    p = PureWindowsPath((process or "").replace("/", "\\")).name.casefold()
    return p in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe") and game_score(title,process) > 0


def _exe_name(pid: int) -> str:
    if os.name != 'nt' or not pid:
        return ''
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    kernel.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD,
                                                  ctypes.wintypes.LPWSTR, ctypes.POINTER(ctypes.wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL
    kernel.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel.CloseHandle.restype = ctypes.wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ''
    try:
        path = ctypes.create_unicode_buffer(32768)
        size = ctypes.wintypes.DWORD(len(path))
        if kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            return path.value
    finally:
        kernel.CloseHandle(handle)
    return ''


def inspect_window(hwnd: int) -> GameWindow | None:
    if os.name != 'nt' or not hwnd:
        return None
    from .capture import title_of
    u = ctypes.windll.user32
    u.GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
    pid = ctypes.wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    title = title_of(hwnd)
    process = _exe_name(pid.value)
    score = game_score(title, process, own_process=(pid.value == os.getpid()))
    return GameWindow(int(hwnd),title,process,int(pid.value),score)


def discover_game_windows() -> list[GameWindow]:
    """Return most likely visible non-minimised game windows, ranked."""
    if os.name != 'nt':
        return []
    u = ctypes.windll.user32
    u.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
    u.IsWindowVisible.restype = ctypes.wintypes.BOOL
    u.IsIconic.argtypes = [ctypes.wintypes.HWND]
    u.IsIconic.restype = ctypes.wintypes.BOOL
    u.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
    u.GetWindowRect.restype = ctypes.wintypes.BOOL
    cbtype = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    u.EnumWindows.argtypes = [cbtype, ctypes.wintypes.LPARAM]
    u.EnumWindows.restype = ctypes.wintypes.BOOL
    found: list[GameWindow] = []

    @cbtype
    def callback(hwnd, _arg):
        try:
            if not u.IsWindowVisible(hwnd) or u.IsIconic(hwnd):
                return True
            rect = ctypes.wintypes.RECT()
            if not u.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            if rect.right - rect.left < 480 or rect.bottom - rect.top < 350:
                return True
            w = inspect_window(int(hwnd))
            if w is not None and w.score >= 60:
                found.append(w)
        except Exception:
            pass
        return True

    u.EnumWindows(callback, 0)
    unique = {w.hwnd: w for w in found}
    return sorted(unique.values(), key=lambda w:(-w.score,w.title.casefold(),w.hwnd))


def choose_unambiguous(candidates: list[GameWindow]) -> GameWindow | None:
    """Select a single high confidence game; ambiguous matches need UI choice."""
    if not candidates:
        return None
    ranked=sorted(candidates,key=lambda w:-w.score)
    if len(ranked)==1 or ranked[0].score-ranked[1].score>=35:
        return ranked[0]
    return None

"""Windows screen capture and offline OCR. No reads of game memory or APIs."""
from __future__ import annotations
import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from PIL import Image

if hasattr(ctypes, "windll"):
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    user32.GetWindowTextW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.RECT)]
    user32.GetWindowRect.restype = ctypes.wintypes.BOOL
    user32.IsWindow.argtypes = [ctypes.wintypes.HWND]
    user32.IsWindow.restype = ctypes.wintypes.BOOL
    user32.IsIconic.argtypes = [ctypes.wintypes.HWND]
    user32.IsIconic.restype = ctypes.wintypes.BOOL
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
else:
    user32 = None


@dataclass(frozen=True)
class Screen:
    image: Image.Image
    left: int
    top: int
    hwnd: int


def foreground_window() -> int:
    return int(user32.GetForegroundWindow()) if user32 else 0


def title_of(hwnd: int) -> str:
    if not user32 or not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def key_down(vk: int) -> bool:
    return bool(user32 and (user32.GetAsyncKeyState(vk) & 0x8000))


def capture_window(hwnd: int) -> Screen:
    if not user32 or not hwnd or not user32.IsWindow(hwnd):
        raise RuntimeError("The selected game window no longer exists. Attach again with F8.")
    from mss import mss
    rect = ctypes.wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("Cannot read the game window bounds.")
    l, t = max(0, rect.left), max(0, rect.top)
    r, b = rect.right, rect.bottom
    if r - l < 400 or b - t < 300 or bool(user32.IsIconic(hwnd)):
        raise RuntimeError("Game window is minimised or too small.")
    with mss() as ss:
        grab = ss.grab({"left": l, "top": t, "width": r-l, "height": b-t})
        im = Image.frombytes("RGB", grab.size, grab.rgb)
    return Screen(im, l, t, hwnd)


def image_region(img: Image.Image, rel: list[float]) -> Image.Image:
    w, h = img.size
    x1, y1, x2, y2 = rel
    return img.crop((int(w*x1), int(h*y1), int(w*x2), int(h*y2)))


class Reader:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.engine = RapidOCR()

    def read(self, img: Image.Image) -> list[tuple[float, float, str, float]]:
        """OCR rows as normalized center X/Y coordinates, text, confidence."""
        import numpy as np
        w, h = img.size
        scale = 1.30 if w < 900 else 1.0
        if scale != 1.0:
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        result, _ = self.engine(np.asarray(img))
        rows = []
        if result:
            for box, value, confidence in result:
                if confidence < 0.46:
                    continue
                cx = sum(float(p[0]) for p in box) / (4 * img.width)
                cy = sum(float(p[1]) for p in box) / (4 * img.height)
                rows.append((cx, cy, str(value), float(confidence)))
        return sorted(rows, key=lambda r: (r[1], r[0]))


def group_cards(rows: list[tuple[float, float, str, float]], count: int) -> list[list[str]]:
    cards: list[list[tuple[float, str]]] = [[] for _ in range(count)]
    for x, y, s, conf in rows:
        column = min(count - 1, max(0, int(x * count)))
        cards[column].append((y, s))
    return [[text for y, text in sorted(card)] for card in cards]

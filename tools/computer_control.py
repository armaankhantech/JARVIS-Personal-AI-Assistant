"""Grounded desktop input helpers for Jarvis.

Coordinates should come from a fresh screenshot or a verified UI rectangle.
Every call is still routed through JarvisAgent and safety_guard before execution.
"""
from __future__ import annotations

import time
import pyautogui
import pyperclip

# Avoid PyAutoGUI's default one-second delay between actions.
pyautogui.PAUSE = 0.08

_KEY_ALIASES = {
    "control": "ctrl", "escape": "esc", "return": "enter",
    "windows": "win", "cmd": "win", "command": "win",
    "delete": "delete", "backspace": "backspace",
}


def _screen_size():
    size = pyautogui.size()
    return int(size.width), int(size.height)


def click(x, y):
    try:
        x, y = int(x), int(y)
        width, height = _screen_size()
        if not (0 <= x < width and 0 <= y < height):
            return {"success": False, "error": f"Coordinates ({x}, {y}) are outside the {width}x{height} screen."}
        pyautogui.click(x, y)
        return {"success": True, "result": f"Click command sent at ({x}, {y}).", "coordinates": {"x": x, "y": y}}
    except Exception as error:
        return {"success": False, "error": f"Click failed: {type(error).__name__}: {error}"}


def double_click(x, y):
    try:
        x, y = int(x), int(y)
        width, height = _screen_size()
        if not (0 <= x < width and 0 <= y < height):
            return {"success": False, "error": f"Coordinates ({x}, {y}) are outside the {width}x{height} screen."}
        pyautogui.doubleClick(x, y, interval=0.08)
        return {"success": True, "result": f"Double-click command sent at ({x}, {y}).", "coordinates": {"x": x, "y": y}}
    except Exception as error:
        return {"success": False, "error": f"Double-click failed: {type(error).__name__}: {error}"}


def type_text(text):
    if not isinstance(text, str):
        return {"success": False, "error": "Text must be a string."}
    try:
        # Clipboard paste handles Unicode and long text more reliably than key-by-key typing.
        pyperclip.copy(text)
        time.sleep(0.06)
        pyautogui.hotkey("ctrl", "v", interval=0.03)
        return {
            "success": True,
            "result": f"Paste command sent for {len(text)} characters; target contents are not independently verified.",
            "characters": len(text),
            "verified": False,
        }
    except Exception as error:
        return {"success": False, "error": f"Text paste failed: {type(error).__name__}: {error}"}


def press_key(key):
    if not isinstance(key, str) or not key.strip():
        return {"success": False, "error": "A valid key or key combination is required."}
    keys = [part.strip().lower() for part in key.split("+")]
    if any(not part for part in keys):
        return {"success": False, "error": "Invalid key combination."}
    keys = [_KEY_ALIASES.get(part, part) for part in keys]
    try:
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys, interval=0.03)
        return {"success": True, "result": f"Keyboard command sent: {'+'.join(keys)}.", "verified": False}
    except Exception as error:
        return {"success": False, "error": f"Keyboard action failed: {type(error).__name__}: {error}"}

"""Windows desktop automation using pywinauto UI Automation.

All window operations target a real, visible title returned by list_windows.
Closing uses a graceful window-close request and never kills processes.
"""
from __future__ import annotations

import time
from typing import Any

from pywinauto import Desktop


def _desktop():
    return Desktop(backend="uia")


def _window_title(window) -> str:
    try:
        return str(window.window_text() or "").strip()
    except Exception:
        return ""


def _find_window(window_title: str):
    if not isinstance(window_title, str) or not window_title.strip():
        raise ValueError("window_title must be a non-empty visible window title.")
    requested = window_title.strip()
    windows = _desktop().windows(visible_only=True)
    candidates = []
    for window in windows:
        title = _window_title(window)
        if not title or title.lower() in {"taskbar", "program manager"}:
            continue
        if title.casefold() == requested.casefold():
            return window
        if requested.casefold() in title.casefold():
            candidates.append(window)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        titles = [_window_title(w) for w in candidates]
        raise ValueError(f"Window title '{requested}' is ambiguous. Matching titles: {titles}")
    raise LookupError(f"No visible window matched '{requested}'. Call list_windows and use an exact returned title.")


def list_windows():
    """Return visible titled windows and handles for grounding later actions."""
    try:
        windows = []
        for window in _desktop().windows(visible_only=True):
            title = _window_title(window)
            if not title or title.casefold() in {"taskbar", "program manager"}:
                continue
            try:
                handle = int(window.handle)
            except Exception:
                handle = None
            windows.append({"title": title, "handle": handle})
        return {"success": True, "windows": windows, "count": len(windows)}
    except Exception as error:
        return {"success": False, "error": f"Could not list windows: {type(error).__name__}: {error}"}


def inspect_window(window_title: str, max_controls: int = 80):
    """Inspect accessible controls in a visible window."""
    try:
        window = _find_window(window_title)
        limit = max(1, min(int(max_controls), 250))
        controls = []
        try:
            descendants = window.descendants()[:limit]
        except Exception:
            descendants = []
        for control in descendants:
            try:
                info = control.element_info
                name = str(getattr(info, "name", "") or "").strip()
                control_type = str(getattr(info, "control_type", "") or "")
                if not name and not control_type:
                    continue
                try:
                    rect = control.rectangle()
                    rectangle = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
                except Exception:
                    rectangle = None
                try:
                    visible = bool(control.is_visible())
                except Exception:
                    visible = None
                try:
                    enabled = bool(control.is_enabled())
                except Exception:
                    enabled = None
                controls.append({"name": name, "control_type": control_type, "visible": visible, "enabled": enabled, "rectangle": rectangle})
            except Exception:
                continue
        return {"success": True, "window": _window_title(window), "controls": controls, "count": len(controls), "truncated": len(controls) >= limit}
    except Exception as error:
        return {"success": False, "error": f"Window inspection failed: {type(error).__name__}: {error}"}


def _find_control(
    window,
    control_name: str,
    control_type: str | None = None,
    automation_id: str | None = None,
    index: int | None = None,
):
    if not isinstance(control_name, str) or not control_name.strip():
        raise ValueError("control_name must be a non-empty name from inspect_window.")

    requested = control_name.strip()
    matches = []

    for control in window.descendants():
        try:
            info = control.element_info
            name = str(getattr(info, "name", "") or "").strip()
            kind = str(getattr(info, "control_type", "") or "")
            auto_id = str(getattr(info, "automation_id", "") or "")

            if name.casefold() != requested.casefold():
                continue
            if control_type and kind.casefold() != control_type.casefold():
                continue
            if automation_id and auto_id != str(automation_id):
                continue

            matches.append(control)
        except Exception:
            continue

    if index is not None:
        if not isinstance(index, int) or index < 0:
            raise ValueError("index must be a non-negative integer.")
        if index >= len(matches):
            raise LookupError(
                f"Control index {index} is outside the {len(matches)} matching controls."
            )
        return matches[index]

    if not matches:
        raise LookupError(
            f"No control matched name={requested!r}, "
            f"control_type={control_type!r}, automation_id={automation_id!r}."
        )

    if len(matches) != 1:
        details = []
        for item in matches:
            try:
                info = item.element_info
                rect = item.rectangle()
                details.append({
                    "name": str(getattr(info, "name", "") or ""),
                    "control_type": str(getattr(info, "control_type", "") or ""),
                    "automation_id": str(getattr(info, "automation_id", "") or ""),
                    "rectangle": {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                    },
                })
            except Exception:
                details.append({"name": requested})
        raise LookupError(
            f"Control name {requested!r} is ambiguous. "
            f"Use control_type, automation_id, or index. Matches: {details}"
        )

    return matches[0]


def click_control(
    window_title: str,
    control_name: str,
    control_type: str | None = None,
    automation_id: str | None = None,
    index: int | None = None,
):
    try:
        window = _find_window(window_title)
        control = _find_control(
            window,
            control_name,
            control_type=control_type,
            automation_id=automation_id,
            index=index,
        )

        try:
            if not control.is_visible() or not control.is_enabled():
                return {
                    "success": False,
                    "verified": False,
                    "error": "The control is not visible or enabled.",
                }
        except Exception:
            pass

        info = control.element_info
        selected_name = str(getattr(info, "name", "") or "").strip()
        selected_type = str(getattr(info, "control_type", "") or "")
        selected_id = str(getattr(info, "automation_id", "") or "")

        control.click_input()
        time.sleep(0.25)

        # Recheck that the target still exists and report its observed state.
        try:
            still_exists = bool(control.exists(timeout=0.5))
        except Exception:
            still_exists = False

        return {
            "success": True,
            "verified": False,
            "window": _window_title(window),
            "control": selected_name,
            "control_type": selected_type,
            "automation_id": selected_id,
            "target_still_exists": still_exists,
            "result": (
                "Click was sent to the uniquely selected control. "
                "The resulting application state has not been independently verified."
            ),
        }

    except Exception as error:
        return {
            "success": False,
            "verified": False,
            "error": f"Control click failed: {type(error).__name__}: {error}",
        }


def type_into_control(window_title: str, control_name: str, text: str):
    if not isinstance(text, str):
        return {"success": False, "error": "text must be a string."}
    try:
        window = _find_window(window_title)
        control = _find_control(window, control_name)
        control_type = str(getattr(control.element_info, "control_type", ""))
        if control_type == "Edit":
            control.set_edit_text(text)
        elif control_type in {"Document", "Text"}:
            control.click_input()
            import pyperclip
            import pyautogui
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        else:
            return {"success": False, "error": f"Control type '{control_type}' is not a supported text-entry control."}
        return {"success": True, "window": _window_title(window), "control": control_name, "result": "Text-entry command sent; the resulting content is not independently verified.", "verified": False}
    except Exception as error:
        return {"success": False, "error": f"Text entry failed: {type(error).__name__}: {error}"}


def activate_window(window_title: str):
    try:
        window = _find_window(window_title)
        try:
            if window.is_minimized():
                window.restore()
        except Exception:
            pass
        window.set_focus()
        return {"success": True, "window": _window_title(window), "result": "Window activation requested."}
    except Exception as error:
        return {"success": False, "error": f"Window activation failed: {type(error).__name__}: {error}"}


def press_key_in_window(window_title: str, key: str):
    if not isinstance(key, str) or not key.strip():
        return {"success": False, "error": "key must be a non-empty key or combination."}
    try:
        window = _find_window(window_title)
        window.set_focus()
        import pyautogui
        aliases = {"control": "ctrl", "escape": "esc", "return": "enter", "windows": "win"}
        keys = [aliases.get(part.strip().lower(), part.strip().lower()) for part in key.split("+")]
        if not all(keys):
            return {"success": False, "error": "Invalid key combination."}
        # Do not use Alt+F4 for closing; close_window is the graceful-close route.
        if [k.lower() for k in keys] == ["alt", "f4"]:
            return {"success": False, "error": "Alt+F4 is disabled. Use close_window for a graceful close request."}
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return {"success": True, "window": _window_title(window), "result": f"Keyboard command sent: {'+'.join(keys)}."}
    except Exception as error:
        return {"success": False, "error": f"Window keyboard action failed: {type(error).__name__}: {error}"}


def close_window(window_title: str, timeout_seconds: float = 2.0):
    """Ask a window to close normally and check whether its handle disappears."""
    try:
        window = _find_window(window_title)
        title = _window_title(window)
        handle = int(window.handle)
        window.close()  # Graceful WM_CLOSE; no process termination.
        deadline = time.monotonic() + max(0.2, min(float(timeout_seconds), 5.0))
        while time.monotonic() < deadline:
            still_present = False
            for candidate in _desktop().windows(visible_only=False):
                try:
                    if int(candidate.handle) == handle:
                        still_present = True
                        break
                except Exception:
                    continue
            if not still_present:
                return {"success": True, "window": title, "result": "Window closed and its handle is no longer present.", "verified": True}
            time.sleep(0.1)
        return {"success": False, "window": title, "error": "Close request was sent, but the window still exists. It may be waiting for confirmation or unsaved changes.", "verified": False}
    except Exception as error:
        return {"success": False, "error": f"Window close failed: {type(error).__name__}: {error}"}

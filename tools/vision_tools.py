"""Screenshot-based UI targeting with strict coordinate validation and verification."""
from __future__ import annotations

import json
import re
import time

import pyautogui
from models.router import ModelRouter
from tools.computer_tools import take_screenshot
from tools.computer_control import click


def _image_path_from_screenshot(result):
    """Accept the screenshot helper's common return shapes without guessing a path."""
    if isinstance(result, str) and result.strip():
        return result
    if isinstance(result, dict) and result.get("success") is True:
        for key in ("result", "path", "image_path", "screenshot"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _parse_json_object(response):
    if not isinstance(response, str):
        raise ValueError("Vision model did not return text.")
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", response.strip(), flags=re.I)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    # Find a complete JSON object while respecting braces inside quoted strings.
    depth = 0
    start = None
    quoted = False
    escaped = False
    for i, char in enumerate(cleaned):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"' and depth:
            quoted = True
        elif char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(cleaned[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    start = None
    raise ValueError("Vision returned invalid JSON.")


def find_on_screen(target):
    if not isinstance(target, str) or not target.strip():
        return {"success": False, "error": "Describe the visible UI element to find."}
    screenshot = take_screenshot()
    image_path = _image_path_from_screenshot(screenshot)
    if not image_path:
        return {"success": False, "error": f"Screenshot failed or returned no image path: {screenshot}"}

    width, height = pyautogui.size()
    prompt = f'''Locate this target in the screenshot: {target!r}.
The screenshot may include the desktop, application title bar, browser tabs and address bar.
Choose the requested target only; do not confuse browser chrome with webpage content.
Coordinates must be integer absolute pixels within {width}x{height}.
Return only one JSON object: {{"found":true,"x":123,"y":456}}.
If not confidently visible, return: {{"found":false,"x":null,"y":null}}.
Do not guess if the target is obscured or ambiguous.'''
    try:
        response = ModelRouter().analyze_image(image_path, prompt)
        data = _parse_json_object(response)
    except Exception as error:
        return {"success": False, "error": f"Could not locate target: {type(error).__name__}: {error}"}

    if data.get("found") is not True:
        return {"success": False, "found": False, "error": f"Target not confidently visible: {target}"}
    x, y = data.get("x"), data.get("y")
    if type(x) is not int or type(y) is not int or not (0 <= x < width and 0 <= y < height):
        return {"success": False, "error": f"Vision returned invalid coordinates for {width}x{height}: x={x!r}, y={y!r}"}
    return {"success": True, "found": True, "x": x, "y": y, "screen": {"width": width, "height": height}, "target": target}


def click_and_verify(target, expected_result):
    """Find a visible target, click it, then use a fresh screenshot to verify."""
    location = find_on_screen(target)
    if not location.get("success"):
        return {"success": False, "stage": "find", "message": location.get("error", f"Could not find {target}"), "location": location}
    x, y = location["x"], location["y"]
    click_result = click(x, y)
    if not isinstance(click_result, dict) or click_result.get("success") is not True:
        return {"success": False, "stage": "click", "message": "Click command failed.", "click_result": click_result}
    time.sleep(0.25)
    screenshot = take_screenshot()
    image_path = _image_path_from_screenshot(screenshot)
    if not image_path:
        return {"success": False, "stage": "verify", "clicked": True, "coordinates": {"x": x, "y": y}, "message": "Click was sent, but a fresh screenshot was unavailable."}
    prompt = f'''Inspect the screenshot taken after a click.
Expected visible result: {expected_result!r}.
Return only JSON: {{"verified":true,"evidence":"brief visible evidence"}}.
If not clearly visible, return {{"verified":false,"evidence":"what is visible or uncertain"}}.
Do not assume success.'''
    try:
        verification = _parse_json_object(ModelRouter().analyze_image(image_path, prompt))
    except Exception as error:
        return {"success": False, "stage": "verify", "clicked": True, "coordinates": {"x": x, "y": y}, "message": f"Click sent, verification failed: {type(error).__name__}: {error}"}
    verified = verification.get("verified") is True
    return {"success": verified, "stage": "complete" if verified else "verify", "clicked": True, "coordinates": {"x": x, "y": y}, "verification": verification}

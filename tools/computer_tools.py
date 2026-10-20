import pyautogui
from pathlib import Path


def take_screenshot():
    screenshot = pyautogui.screenshot()

    folder = Path("data")
    folder.mkdir(exist_ok=True)

    path = folder / "screenshot.png"
    screenshot.save(path)

    return str(path)
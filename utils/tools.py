# tools
import time

import Levenshtein
import pyautogui

from .log import error
from .mouse import move_to_position


def sleep(seconds=1):
    time.sleep(seconds)


def get_secs(seconds=1):
    return seconds


def drag_scroll(mousePos, to):
    """to: negative to scroll down, positive to scroll up"""
    if not to or not mousePos:
        error("drag_scroll correct variables not supplied.")
    move_to_position(mousePos, duration=0.1)
    pyautogui.mouseDown()
    pyautogui.moveRel(0, to, duration=0.25)
    pyautogui.mouseUp()
    pyautogui.click()


def closest_text_match(text: str, options: list[str], threshold: float = 0.8) -> str:
    for option in options:
        similarity = Levenshtein.ratio(text.lower(), option.lower())
        if similarity >= threshold:
            return option
    return ""

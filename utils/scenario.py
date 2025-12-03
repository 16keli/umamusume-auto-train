import pyautogui

from core.recognizer import match_template
from core.state import GlobalState
from utils.mouse import move_to_center_of_box
from utils.screenshot import ensure_screenshot


def ura(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, existing_screen=existing_screen)
    boxes = match_template(state.asset_by_path("assets/ura/ura_race_btn.png"), existing_screen, threshold=0.8)
    if boxes:
        move_to_center_of_box(boxes[0], duration=0.2)
        pyautogui.click()

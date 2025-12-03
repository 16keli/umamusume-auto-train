import pyautogui

from core.global_state import GlobalState
from core.ocr import extract_text
from core.recognizer import is_btn_active, match_template
from utils.log import info
from utils.mouse import move_to_position
from utils.screenshot import apply_offset_to_tuple, crop_image
from utils.tools import closest_text_match, drag_scroll, sleep


def buy_skill(state: GlobalState):
    move_to_position(state.data.region.SCROLLING_SELECTION_MOUSE_POS)
    found = False

    for i in range(10):
        if i > 8:
            sleep(0.5)
        screen = state.screenshot()
        buy_skill_icon = match_template(state.asset_by_path("assets/icons/buy_skill.png"), screen, threshold=0.9)

        if buy_skill_icon:
            for x, y, w, h in buy_skill_icon:

                region = (x, y, w, h)
                region = apply_offset_to_tuple(region, state.data.region.SKILL_NAME_OFFSET)
                print(region)
                screenshot = crop_image(screen, region)
                text = extract_text(screenshot)
                if closest_text_match(text, state.config.skill.skill_list):
                    button_region = (x, y, w, h)
                    if is_btn_active(crop_image(screen, button_region)):
                        info(f"Buy {text}")
                        pyautogui.click(x=x + 5, y=y + 5, duration=0.15)
                        found = True
                    else:
                        info(f"{text} found but not enough skill points.")

        drag_scroll(state.data.region.SKILL_SCROLL_BOTTOM_MOUSE_POS, -450)

    return found

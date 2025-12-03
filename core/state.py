import re
from math import floor
from string import ascii_letters

import cv2
import numpy as np

from core.data.config import Mood
from core.global_state import GlobalState
from core.ocr import extract_number, extract_text
from core.recognizer import (
    closest_color,
    count_pixels_of_color,
    match_template,
    multi_match_templates,
)
from utils.log import debug, info, warning
from utils.screen import scale_value_for_screen_height
from utils.screenshot import adjust_box_for_region, ensure_screenshot
from utils.tools import closest_text_match


# Get Stat
def stat_state(state: GlobalState):
    stat_regions = {
        "spd": state.data.region.SPD_STAT_REGION,
        "sta": state.data.region.STA_STAT_REGION,
        "pwr": state.data.region.PWR_STAT_REGION,
        "guts": state.data.region.GUTS_STAT_REGION,
        "wit": state.data.region.WIT_STAT_REGION,
    }

    result = {}
    for stat, region in stat_regions.items():
        img = state.screenshot(region)
        val = extract_number(img)
        result[stat] = val
    return result


# Check support card in each training
def check_support_card(state: GlobalState, threshold=0.8, target="none"):
    SUPPORT_ICONS = {
        "spd": state.asset_by_path("assets/icons/support_card_type_spd.png"),
        "sta": state.asset_by_path("assets/icons/support_card_type_sta.png"),
        "pwr": state.asset_by_path("assets/icons/support_card_type_pwr.png"),
        "guts": state.asset_by_path("assets/icons/support_card_type_guts.png"),
        "wit": state.asset_by_path("assets/icons/support_card_type_wit.png"),
        "friend": state.asset_by_path("assets/icons/support_card_type_friend.png"),
    }

    count_result = {}

    SUPPORT_FRIEND_LEVELS = {
        "gray": [110, 108, 120],
        "blue": [42, 192, 255],
        "green": [162, 230, 30],
        "yellow": [255, 173, 30],
        "max": [255, 235, 120],
    }

    count_result["total_supports"] = 0
    count_result["total_hints"] = 0
    count_result["total_friendship_levels"] = {}
    count_result["hints_per_friend_level"] = {}

    for friend_level, color in SUPPORT_FRIEND_LEVELS.items():
        count_result["total_friendship_levels"][friend_level] = 0
        count_result["hints_per_friend_level"][friend_level] = 0

    screen = state.screenshot(region=state.data.region.SUPPORT_CARD_ICON_BBOX)
    cv2.imwrite("debug/support_card_bbox.png", screen)
    hint_matches = match_template(state.asset_by_path("assets/icons/support_hint.png"), screen, threshold)

    for key, icon in SUPPORT_ICONS.items():
        count_result[key] = {}
        count_result[key]["supports"] = 0
        count_result[key]["hints"] = 0
        count_result[key]["friendship_levels"] = {}

        for friend_level, color in SUPPORT_FRIEND_LEVELS.items():
            count_result[key]["friendship_levels"][friend_level] = 0

        matches = match_template(icon, screen, threshold)
        for match in matches:
            # add the support as a specific key
            count_result[key]["supports"] += 1
            # also add it to the grand total
            count_result["total_supports"] += 1

            # find friend colors and add them to their specific colors
            x, y, w, h = match
            match_horizontal_middle = floor((2 * x + w) / 2)
            match_vertical_middle = floor((2 * y + h) / 2)
            icon_to_friend_bar_distance = scale_value_for_screen_height(132, state.game_window.height)
            bbox_left = match_horizontal_middle + state.data.region.SUPPORT_CARD_ICON_BBOX.x1
            bbox_top = match_vertical_middle + state.data.region.SUPPORT_CARD_ICON_BBOX.y1 + icon_to_friend_bar_distance
            wanted_pixel = (bbox_left, bbox_top, bbox_left + 1, bbox_top + 1)
            wanted_screen = state.screenshot(region=wanted_pixel)  # TODO: consider pulling this out but I'm lazy
            friendship_level_color = wanted_screen[0][0]
            friend_level = closest_color(SUPPORT_FRIEND_LEVELS, friendship_level_color)
            count_result[key]["friendship_levels"][friend_level] += 1
            count_result["total_friendship_levels"][friend_level] += 1

            if hint_matches:
                for hint_match in hint_matches:
                    distance = abs(hint_match[1] - match[1])
                    if distance < 45:
                        count_result["total_hints"] += 1
                        count_result[key]["hints"] += 1
                        count_result["hints_per_friend_level"][friend_level] += 1

    return count_result


# Get failure chance (idk how to get energy value)
def check_failure(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.FAILURE_REGION, existing_screen)
    cv2.imwrite("debug/failure.png", existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    failure_text = extract_text(existing_screen).lower()

    if not failure_text.startswith("failure"):
        return -1

    # SAFE CHECK
    # 1. If there is a %, extract the number before the %
    match_percent = re.search(r"failure\s+(\d{1,3})%", failure_text)
    if match_percent:
        return int(match_percent.group(1))

    # 2. If there is no %, but there is a 9, extract digits before the 9
    match_number = re.search(r"failure\s+(\d+)", failure_text)
    if match_number:
        digits = match_number.group(1)
        idx = digits.find("9")
        if idx > 0:
            num = digits[:idx]
            return int(num) if num.isdigit() else -1
        elif digits.isdigit():
            return int(digits)  # fallback

    return -1


# Check mood
def check_mood(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.MOOD_REGION, existing_screen)
    mood_text_raw = extract_text(existing_screen).upper().strip()
    mood_text = closest_text_match(mood_text_raw, [mood.name for mood in Mood]) or Mood.UNKNOWN.name

    try:
        return Mood[mood_text]
    except ValueError:
        warning(f"Mood not recognized: {mood_text_raw}")
        return Mood.UNKNOWN


# Check turn
def check_turn(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.TURN_REGION, existing_screen)
    cv2.imwrite("debug/turn.png", existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    turn_text = extract_text(existing_screen)

    info(f"Read turn as {turn_text}")

    if "Race Day" in turn_text or closest_text_match(turn_text, ["Race Day"], threshold=0.5):
        return "Race Day"
    # sometimes easyocr misreads characters instead of numbers

    cleaned_text = turn_text.replace("T", "1").replace("I", "1").replace("O", "0").replace("S", "5")

    digits_only = re.sub(r"[^\d]", "", cleaned_text)

    if digits_only:
        return int(digits_only)

    return -1


# Check year
def check_current_year(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.YEAR_REGION, existing_screen)
    cv2.imwrite("debug/year.png", existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_text(existing_screen)
    return text


# Check criteria
def check_criteria(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.CRITERIA_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_text(existing_screen)
    return text


def check_criteria_detail(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.CRITERIA_DETAIL_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_text(existing_screen)
    return text


def check_skill_pts(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.SKILL_PTS_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_number(existing_screen)
    return text


def check_energy_level(state: GlobalState, threshold=0.85):
    # find where the right side of the bar is on screen

    energy_bar_screen = state.screenshot(state.data.region.ENERGY_BBOX)
    # cv2.imwrite("debug/energy.png", energy_bar_screen)

    right_bar_template = state.asset_by_path("assets/ui/energy_bar_right_end_part.png")
    right_bar_match = match_template(right_bar_template, energy_bar_screen, threshold)
    # longer energy bars get more round at the end
    if not right_bar_match:
        right_bar_template_2 = state.asset_by_path("assets/ui/energy_bar_right_end_part_2.png")
        right_bar_match = match_template(right_bar_template_2, energy_bar_screen, threshold)

    left_bar_template = state.asset_by_path("assets/ui/energy_bar_left_end_part.png")
    left_bar_match = match_template(left_bar_template, energy_bar_screen, threshold)

    if right_bar_match and left_bar_match:
        # Can sometimes clip the mood bar, so if that happens we'll choose the leftmost one
        if len(left_bar_match) > 1:
            info(f"Foudn multiple left bar matches: {left_bar_match}")
            left_bar_match = min(left_bar_match, key=lambda box: box[0])
        else:
            left_bar_match = left_bar_match[0]

        energy_bar_length = int(right_bar_match[0][0] - left_bar_match[0])

        top_bottom_middle_pixel = left_bar_match[1] + left_bar_match[3] // 2

        max_energy_bbox = (left_bar_match[0], top_bottom_middle_pixel, energy_bar_length, 1)
        max_energy_bbox = adjust_box_for_region(max_energy_bbox, state.data.region.ENERGY_BBOX)
        info(f"Max energy box at {max_energy_bbox}")

        # [117,117,117] is gray for missing energy, region templating for this one is a problem, so we do this
        max_energy_screen = state.screenshot(max_energy_bbox)
        cv2.imwrite("debug/max_energy.png", max_energy_screen)
        empty_energy_pixel_count = count_pixels_of_color([117, 117, 117], max_energy_screen)

        # use the energy_bar_length (a few extra pixels from the outside are remaining so we subtract that)
        total_energy_length = energy_bar_length - 1
        # counted pixels from one end of the bar to the other
        hundred_energy_pixel_constant = scale_value_for_screen_height(
            468, state.game_window.height
        )  # 4k baseline is 468 pixels

        state.memo.previous_right_bar_match = right_bar_match

        energy_level = ((total_energy_length - empty_energy_pixel_count) / hundred_energy_pixel_constant) * 100
        info(
            f"Total energy bar length = {total_energy_length}, Empty energy pixel count = {empty_energy_pixel_count}, Diff = {(total_energy_length - empty_energy_pixel_count)}"
        )
        info(f"Remaining energy guestimate = {energy_level:.2f}")
        max_energy = total_energy_length / hundred_energy_pixel_constant * 100
        return energy_level, max_energy
    else:
        warning("Couldn't find energy bar, returning -1")
        warning(f"Left box: {left_bar_match}, Right box: {right_bar_match}")
        return -1, -1


def get_race_type(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.RACE_INFO_TEXT_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_text(existing_screen)
    debug(f"Race info text: {text}")
    return text


# Severity -> 0 is doesn't matter / incurable, 1 is "can be ignored for a few turns", 2 is "must be cured immediately"
BAD_STATUS_EFFECTS = {
    "Migraine": {
        "Severity": 2,
        "Effect": "Mood cannot be increased",
    },
    "Night Owl": {
        "Severity": 1,
        "Effect": "Character may lose energy, and possibly mood",
    },
    "Practice Poor": {
        "Severity": 1,
        "Effect": "Increases chance of training failure by 2%",
    },
    "Skin Outbreak": {
        "Severity": 1,
        "Effect": "Character's mood may decrease by one stage.",
    },
    "Slacker": {
        "Severity": 2,
        "Effect": "Character may not show up for training.",
    },
    "Slow Metabolism": {
        "Severity": 2,
        "Effect": "Character cannot gain Speed from speed training.",
    },
    "Under the Weather": {
        "Severity": 0,
        "Effect": "Increases chance of training failure by 5%",
    },
}

GOOD_STATUS_EFFECTS = {
    "Charming": "Raises Friendship Bond gain by 2",
    "Fast Learner": "Reduces the cost of skills by 10%",
    "Hot Topic": "Raises Friendship Bond gain for NPCs by 2",
    "Practice Perfect": "Lowers chance of training failure by 2%",
    "Shining Brightly": "Lowers chance of training failure by 5%",
}


def check_status_effects(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.FULL_STATS_STATUS_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    cv2.imwrite("debug/status.png", existing_screen)

    # debug_window(screen)

    status_effects_text = extract_text(existing_screen, allowlist=ascii_letters)
    debug(f"Status effects text: {status_effects_text}")

    normalized_text = status_effects_text.lower().replace(" ", "")

    matches = [k for k in BAD_STATUS_EFFECTS if k.lower().replace(" ", "") in normalized_text]

    total_severity = sum(BAD_STATUS_EFFECTS[k]["Severity"] for k in matches)

    debug(f"Matches: {matches}, severity: {total_severity}")
    return matches, total_severity


def check_aptitudes(state: GlobalState, existing_screen=None):

    existing_screen = ensure_screenshot(state, state.data.region.FULL_STATS_APTITUDE_REGION, existing_screen)
    h, w = existing_screen.shape[:2]

    # Ratios for each aptitude box (x, y, width, height) in percentages
    boxes = {
        "surface_turf": (0.0, 0.00, 0.25, 0.33),
        "surface_dirt": (0.25, 0.00, 0.25, 0.33),
        "distance_sprint": (0.0, 0.33, 0.25, 0.33),
        "distance_mile": (0.25, 0.33, 0.25, 0.33),
        "distance_medium": (0.50, 0.33, 0.25, 0.33),
        "distance_long": (0.75, 0.33, 0.25, 0.33),
        "style_front": (0.0, 0.66, 0.25, 0.33),
        "style_pace": (0.25, 0.66, 0.25, 0.33),
        "style_late": (0.50, 0.66, 0.25, 0.33),
        "style_end": (0.75, 0.66, 0.25, 0.33),
    }

    aptitude_images = {
        "a": state.asset_by_path("assets/ui/aptitude_a.png"),
        "b": state.asset_by_path("assets/ui/aptitude_b.png"),
        "c": state.asset_by_path("assets/ui/aptitude_c.png"),
        "d": state.asset_by_path("assets/ui/aptitude_d.png"),
        "e": state.asset_by_path("assets/ui/aptitude_e.png"),
        "f": state.asset_by_path("assets/ui/aptitude_f.png"),
        "g": state.asset_by_path("assets/ui/aptitude_g.png"),
    }

    crops = {}
    for key, (xr, yr, wr, hr) in boxes.items():
        x, y, ww, hh = int(xr * w), int(yr * h), int(wr * w), int(hr * h)
        cropped_image = np.array(existing_screen[y : y + hh, x : x + ww])
        matches = multi_match_templates(aptitude_images, cropped_image)
        for name, match in matches.items():
            if match:
                state.memo.aptitudes[key] = name
                # debug_window(cropped_image)

    info(
        f"Parsed aptitude values: {state.memo.aptitudes}. If these values are wrong, please stop and start the bot again with the hotkey."
    )


def debug_window(screen, x=-1400, y=-100):
    cv2.namedWindow("image")
    cv2.moveWindow("image", x, y)
    cv2.imshow("image", screen)
    cv2.waitKey(0)

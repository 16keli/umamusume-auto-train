import re

import pyautogui

from core.data.config import MOOD_VALUE
from core.events import event_choice, get_event_name
from core.global_state import GlobalState
from core.logic import decide_race_for_goal, do_something
from core.recognizer import is_btn_active, match_template, multi_match_templates
from core.skill import buy_skill
from core.state import (
    check_aptitudes,
    check_criteria,
    check_current_year,
    check_energy_level,
    check_failure,
    check_mood,
    check_skill_pts,
    check_status_effects,
    check_support_card,
    check_turn,
    get_race_type,
)
from utils.log import debug, info, warning
from utils.mouse import move_to, move_to_center_of_box, move_to_position
from utils.scenario import ura
from utils.screen import scale_value_for_screen_height
from utils.screenshot import adjust_box_for_region, crop_image, ensure_screenshot
from utils.tools import drag_scroll, get_secs, sleep


def click_box(
    clicks: int = 1,
    text: str = "",
    boxes: list[tuple[int, int, int, int]] | tuple[int, int, int, int] | None = None,
    region=None,
):
    """Click the center of the given box, or first box if there are multiple."""
    if boxes:
        if isinstance(boxes, list):
            if len(boxes) == 0:
                return False
            box = boxes[0]
        else:
            box = boxes

        if text:
            debug(text)
        if region is not None:
            box = adjust_box_for_region(box, region)
        move_to_center_of_box(box)
        pyautogui.click(clicks=clicks, interval=0.15)
        return True

    return False


def click(
    state: GlobalState,
    img: str = None,
    confidence: float = 0.8,
    minSearch: float = 2,
    clicks: int = 1,
    text: str = "",
    boxes=None,
    region=None,
    existing_screen=None,
):
    if not boxes:
        if img is None:
            return False
        screen = ensure_screenshot(state, region, existing_screen)
        boxes = match_template(state.asset_by_path(img), screen, threshold=confidence)

    return click_box(clicks=clicks, text=text, boxes=boxes, region=region)


def keep_try_click(
    state: GlobalState, img: str, clicks: int = 1, interval: float = 0.5, threshold=0.8, timeout: float = 5
) -> list:
    """Waits for a template to be visible on the screen, then clicks it.

    Checks for matches every interval seconds, up to timeout.
    If no match is found then, an empty list is returned.
    """
    time_elapsed = 0.0
    while time_elapsed <= timeout:
        if click(state, img, clicks=clicks, confidence=threshold):
            return True

        sleep(interval)
        time_elapsed += interval

    return False


def go_to_training(state: GlobalState):
    return click(state, img="assets/buttons/training_btn.png")


def check_training(state: GlobalState):
    results = {}

    training_types = {
        "spd": state.asset_by_path("assets/icons/train_spd.png"),
        "sta": state.asset_by_path("assets/icons/train_sta.png"),
        "pwr": state.asset_by_path("assets/icons/train_pwr.png"),
        "guts": state.asset_by_path("assets/icons/train_guts.png"),
        "wit": state.asset_by_path("assets/icons/train_wit.png"),
    }

    # failcheck enum "train","no_train","check_all"
    failcheck = "check_all"
    margin = 5
    screen = state.screenshot(region=state.data.region.SCREEN_BOTTOM_REGION)

    pyautogui.mouseDown()

    for key, icon in training_types.items():

        boxes = match_template(icon, screen, threshold=0.8)

        if boxes:
            move_to(
                boxes[0][0] + state.data.region.SCREEN_BOTTOM_REGION.x1 + boxes[0][2] // 2,
                boxes[0][1] + state.data.region.SCREEN_BOTTOM_REGION.y1 + boxes[0][3] // 2,
            )
            # Sometimes it doesn't pop up yet om
            # sleep a little to allow for the ui to load properly
            sleep(0.2)
            support_card_results = check_support_card(state)

            if key != "wit":
                if failcheck == "check_all":
                    failure_chance = check_failure(state)
                    if failure_chance > (state.config.maximum_failure + margin):
                        info("Failure rate too high skip to check wit")
                        failcheck = "no_train"
                        failure_chance = state.config.maximum_failure + margin
                    elif failure_chance < (state.config.maximum_failure - margin):
                        info("Failure rate is low enough, skipping the rest of failure checks.")
                        failcheck = "train"
                        failure_chance = 0
                elif failcheck == "no_train":
                    failure_chance = state.config.maximum_failure + margin
                elif failcheck == "train":
                    failure_chance = 0
            else:
                if failcheck == "train":
                    failure_chance = 0
                else:
                    failure_chance = check_failure(state)

            support_card_results["failure"] = failure_chance
            results[key] = support_card_results

            debug(
                f"[{key.upper()}] → Total Supports {support_card_results['total_supports']}, Levels:{support_card_results['total_friendship_levels']} , Fail: {failure_chance}%"
            )
            sleep(0.1)
        else:
            warning(f"Couldn't find training icon for {key}")

    pyautogui.mouseUp()
    click(state, img="assets/buttons/back_btn.png")
    return results


def do_train(state: GlobalState, train):
    if click(
        state,
        img=f"assets/icons/train_{train}.png",
        confidence=0.8,
        region=state.data.region.SCREEN_BOTTOM_REGION,
        clicks=3,
    ):
        pass
    else:
        warning(f"Couldn't find {train} training button.")


def do_rest(state: GlobalState, energy_level):
    if state.config.never_rest_energy > 0 and energy_level > state.config.never_rest_energy:
        info(f"Wanted to rest when energy was above {state.config.never_rest_energy}, retrying from beginning.")
        return

    if click(state, img="assets/buttons/rest_btn.png", confidence=0.8, region=state.data.region.SCREEN_BOTTOM_REGION):
        pass
    elif click(
        state, img="assets/buttons/rest_summer_btn.png", confidence=0.8, region=state.data.region.SCREEN_BOTTOM_REGION
    ):
        pass
    else:
        warning("Couldn't find rest button.")


def do_recreation(state: GlobalState):
    if click(
        state, img="assets/buttons/recreation_btn.png", confidence=0.8, region=state.data.region.SCREEN_BOTTOM_REGION
    ):
        pass
    elif click(
        state, img="assets/buttons/rest_summer_btn.png", confidence=0.8, region=state.data.region.SCREEN_BOTTOM_REGION
    ):
        pass
    else:
        warning("Couldn't find recreation button.")


def do_race(state: GlobalState, race=None):
    click(state, img="assets/buttons/races_btn.png")

    consecutive_cancel_btn_box = match_template(
        state.asset_by_path("assets/buttons/cancel_btn.png"), state.screenshot(), threshold=0.8
    )
    if state.config.cancel_consecutive_race and consecutive_cancel_btn_box:
        click_box(
            boxes=consecutive_cancel_btn_box,
            text="[INFO] Already raced 3+ times consecutively. Cancelling race and doing training.",
        )
        return False
    elif not state.config.cancel_consecutive_race and consecutive_cancel_btn_box:
        click(state, img="assets/buttons/ok_btn.png")

    sleep(0.7)
    found = race_select(state, race=race)
    if not found:
        if race is not None:
            info(f"{race} not found.")
        else:
            info("Race not found.")
        return False

    race_prep(state)
    sleep(1)
    after_race(state)
    return True


def select_event(state: GlobalState):
    event_choices_icon_box = match_template(
        state.asset_by_path("assets/icons/event_choice_1.png"),
        state.screenshot(state.data.region.GAME_SCREEN_REGION),
        threshold=0.9,
    )
    choice_vertical_gap = scale_value_for_screen_height(224, state.game_window.height)

    if not event_choices_icon_box:
        return False

    if not state.config.event.use_optimal_event_choice:
        click_box(
            boxes=event_choices_icon_box,
            text="Event found, selecting top choice.",
            region=state.data.region.GAME_SCREEN_REGION,
        )
        return True

    event_name = get_event_name(state)

    chosen = event_choice(state, event_name)
    if chosen == 0:
        click_box(
            boxes=event_choices_icon_box,
            text="Event found, selecting top choice.",
            region=state.data.region.GAME_SCREEN_REGION,
        )
        return True

    x = event_choices_icon_box[0][0]
    y = event_choices_icon_box[0][1] + ((chosen - 1) * choice_vertical_gap)
    debug(f"Event choices coordinates: {event_choices_icon_box[0]}")
    debug(f"Clicking: {x}, {y}")
    click_box(
        boxes=(x, y, 1, 1), text=f"Selecting optimal choice: {event_name}", region=state.data.region.GAME_SCREEN_REGION
    )
    return True


def race_day(state: GlobalState):
    keep_try_click(state, img="assets/buttons/race_day_btn.png")

    click(state, img="assets/buttons/ok_btn.png")
    sleep(0.5)

    # move mouse off the race button so that image can be matched
    #  pyautogui.moveTo(x=400, y=400)

    race_prep(state)
    sleep(1)
    after_race(state)


def race_select(state: GlobalState, race=None):
    move_to_position(state.data.region.SCROLLING_SELECTION_MOUSE_POS)

    sleep(0.3)

    if state.config.prioritize_g1_race and race is not None:
        info(f"Looking for {race}.")
        for i in range(2):
            if click(
                state,
                img=f"assets/races/{race}.png",
                text=f"{race} found.",
                region=state.data.region.RACE_LIST_BOX_REGION,
            ):
                return True
            drag_scroll(state.data.region.RACE_SCROLL_BOTTOM_MOUSE_POS, -270)

        return False
    else:
        info("Looking for race.")
        for i in range(4):
            screen = state.screenshot()
            match_aptitude = match_template(
                state.asset_by_path("assets/ui/match_track.png"),
                screen,
                threshold=0.8,
            )

            if match_aptitude:
                # locked avg brightness = 163
                # unlocked avg brightness = 230
                match_aptitude_box = crop_image(screen, match_aptitude[0])
                if not is_btn_active(match_aptitude_box, threshold=200):
                    info("Race found, but it's locked.")
                    return False
                info("Race found.")
                click(state, boxes=match_aptitude)
                return True
            drag_scroll(state.data.region.RACE_SCROLL_BOTTOM_MOUSE_POS, -270)

        return False


def race_prep(state: GlobalState):
    # om
    if not keep_try_click(state, img="assets/buttons/race_btn.png"):
        warning("Where first race button?")
    if not keep_try_click(state, img="assets/buttons/race_btn.png"):
        warning("Where second race button?")

    if state.config.position_selection_enabled:
        # these two are mutually exclusive, so we only use preferred position if positions by race is not enabled.
        if state.config.enable_positions_by_race:
            click(state, img="assets/buttons/info_btn.png", region=state.data.region.SCREEN_TOP_REGION)
            sleep(0.5)
            # find race text, get part inside parentheses using regex, strip whitespaces and make it lowercase for our usage
            race_info_text = get_race_type(state)
            match_race_type = re.search(r"\(([^)]+)\)", race_info_text)
            race_type = match_race_type.group(1).strip().lower() if match_race_type else None
            click(state, img="assets/buttons/close_btn.png", region=state.data.region.SCREEN_BOTTOM_REGION)

            if race_type is not None:
                position_for_race = state.config.positions_by_race[race_type].value
                info(f"Selecting position {position_for_race} based on race type {race_type}")
                click(
                    state,
                    img="assets/buttons/change_btn.png",
                    region=state.data.region.SCREEN_MIDDLE_REGION,
                )
                click(
                    state,
                    img=f"assets/buttons/positions/{position_for_race}_position_btn.png",
                    region=state.data.region.SCREEN_MIDDLE_REGION,
                )
                click(
                    state,
                    img="assets/buttons/confirm_btn.png",
                    region=state.data.region.SCREEN_MIDDLE_REGION,
                )
        elif not state.memo.preferred_position_set:
            click(state, img="assets/buttons/change_btn.png", region=state.data.region.SCREEN_MIDDLE_REGION)
            click(
                state,
                img=f"assets/buttons/positions/{state.config.preferred_position.value}_position_btn.png",
                region=state.data.region.SCREEN_MIDDLE_REGION,
            )
            click(state, img="assets/buttons/confirm_btn.png", region=state.data.region.SCREEN_MIDDLE_REGION)
            state.memo.preferred_position_set = True

    # view_results_screen = state.screenshot(state.data.region.SCREEN_BOTTOM_REGION)
    # cv2.imwrite("debug/view_results_screen.png", view_results_screen)
    # view_results_template = state.asset_by_path("assets/buttons/view_results.png")
    # cv2.imwrite("debug/view_results_template.png", cv2.cvtColor(view_results_template, cv2.COLOR_RGB2GRAY))
    # view_results_boxes = match_template(view_results_template, view_results_screen)

    if not keep_try_click(state, img="assets/buttons/view_results.png", clicks=3):
        warning("Couldn't find view results button to click")

    sleep(0.5)
    pyautogui.click()
    sleep(0.1)
    move_to_position(state.data.region.SCROLLING_SELECTION_MOUSE_POS)

    for i in range(2):
        pyautogui.tripleClick(interval=0.2)
        sleep(0.5)
    pyautogui.click()
    next_button_boxes = match_template(
        state.asset_by_path("assets/buttons/next_btn.png"),
        state.screenshot(state.data.region.SCREEN_BOTTOM_REGION),
        threshold=0.9,
    )
    if not next_button_boxes:
        info("Wouldn't be able to move onto the after race since there's no next button.")
        if click(
            state, img="assets/buttons/race_btn.png", confidence=0.8, region=state.data.region.SCREEN_BOTTOM_REGION
        ):
            info(f"Went into the race, sleep for {get_secs(10)} seconds to allow loading.")
            sleep(10)
            race_screen = state.screenshot()
            if not click(
                state, img="assets/buttons/race_exclamation_btn.png", confidence=0.8, existing_screen=race_screen
            ):
                info('Couldn\'t find "Race!" button, looking for alternative version.')
                click(
                    state,
                    img="assets/buttons/race_exclamation_btn_portrait.png",
                    confidence=0.8,
                    existing_screen=race_screen,
                )
            sleep(0.5)

            look_for_skip_screen = state.screenshot()

            skip_btn_boxes = match_template(
                state.asset_by_path("assets/buttons/skip_btn.png"),
                crop_image(look_for_skip_screen, state.data.region.SCREEN_BOTTOM_REGION),
                threshold=0.8,
            )
            skip_btn_big_boxes = match_template(
                state.asset_by_path("assets/buttons/skip_btn_big.png"),
                crop_image(look_for_skip_screen, state.data.region.SKIP_BTN_BIG_REGION_LANDSCAPE),
                threshold=0.8,
            )

            # TODO: original implementation uses pyautogui.locateOnScreen, which takes multiple screenshots internally.
            # see if we need to do this, though I suspect one screenshot is enough.

            # Also not sure why we're clicking infinite here. I guess since this is logic for actually watching the race
            if skip_btn_boxes:
                click_box(boxes=skip_btn_boxes, clicks=3)
            if skip_btn_big_boxes:
                click_box(boxes=skip_btn_big_boxes, clicks=3)
            sleep(3)
            if skip_btn_boxes:
                click_box(boxes=skip_btn_boxes, clicks=3)
            if skip_btn_big_boxes:
                click_box(boxes=skip_btn_big_boxes, clicks=3)
            sleep(0.5)
            if skip_btn_boxes:
                click_box(boxes=skip_btn_boxes, clicks=3)
            if skip_btn_big_boxes:
                click_box(boxes=skip_btn_big_boxes, clicks=3)
            sleep(3)

            skip_btn_boxes = match_template(
                state.asset_by_path("assets/buttons/skip_btn.png"),
                state.screenshot(state.data.region.SCREEN_BOTTOM_REGION),
                threshold=0.8,
            )
            click_box(boxes=skip_btn_boxes, clicks=3)
            # since we didn't get the trophy before, if we get it we close the trophy
            close_btn_boxes = match_template(
                state.asset_by_path("assets/buttons/close_btn.png"), state.screenshot(), threshold=0.8
            )
            click_box(boxes=close_btn_boxes, clicks=3)
            info("Finished race skipping job.")


def after_race(state: GlobalState, existing_screen=None):
    click(state, img="assets/buttons/next_btn.png", existing_screen=existing_screen)
    sleep(0.3)
    pyautogui.click()
    click(state, img="assets/buttons/next2_btn.png", existing_screen=existing_screen)


def auto_buy_skill(state: GlobalState, existing_screen=None):
    if check_skill_pts(state) < state.config.skill.skill_pts_check:
        return

    click(state, img="assets/buttons/skills_btn.png", existing_screen=existing_screen)
    info("Buying skills")
    sleep(0.5)

    if buy_skill(state):
        keep_try_click(
            state,
            img="assets/buttons/confirm_btn.png",
        )
        keep_try_click(
            state,
            img="assets/buttons/learn_btn.png",
        )
        keep_try_click(
            state,
            img="assets/buttons/close_btn.png",
        )
        keep_try_click(state, img="assets/buttons/back_btn.png")
    else:
        info("No matching skills found. Going back.")
        keep_try_click(state, img="assets/buttons/back_btn.png")


def career_lobby(state: GlobalState):
    # Program start

    templates = {
        "event": state.asset_by_path("assets/icons/event_choice_1.png"),
        "inspiration": state.asset_by_path("assets/buttons/inspiration_btn.png"),
        "next": state.asset_by_path("assets/buttons/next_btn.png"),
        "next2": state.asset_by_path("assets/buttons/next2_btn.png"),
        "cancel": state.asset_by_path("assets/buttons/cancel_btn.png"),
        "tazuna": state.asset_by_path("assets/ui/tazuna_hint.png"),
        "infirmary": state.asset_by_path("assets/buttons/infirmary_btn.png"),
        "retry": state.asset_by_path("assets/buttons/retry_btn.png"),
    }

    while state.bot.is_bot_running and not state.bot.stop_event.is_set():
        screen = state.screenshot()
        matches = multi_match_templates(templates, screen=screen)
        # Image.fromarray(screen).show()

        if select_event(state):
            debug("Event selected.")
            continue
        if click_box(boxes=matches["inspiration"], text="Inspiration found."):
            debug("Getting inspiration boost.")
            continue
        if click_box(boxes=matches["next"]):
            debug("Next!")
            continue
        if click_box(boxes=matches["next2"]):
            debug("Next!")
            continue
        if click_box(boxes=matches["cancel"]):
            debug("Cancelling...")
            continue
        if click_box(boxes=matches["retry"]):
            debug("Retrying...")
            continue

        if not matches["tazuna"]:
            # warning("Should be in career lobby.")
            print(".", end="")
            continue

        energy_level, max_energy = check_energy_level(state)

        skipped_infirmary = False
        if matches["infirmary"]:
            infirmary_button = crop_image(screen, matches["infirmary"][0])
            if is_btn_active(infirmary_button):
                # infirmary always gives 20 energy, it's better to spend energy before going to the infirmary 99% of the time.
                if max(0, (max_energy - energy_level)) >= state.config.skip_infirmary_unless_missing_energy:
                    click(state, boxes=matches["infirmary"][0], text="Character debuffed, going to infirmary.")
                    continue
                else:
                    info("Skipping infirmary because of high energy.")
                    skipped_infirmary = True

        mood = check_mood(state, screen)
        mood_index = MOOD_VALUE[mood]
        minimum_mood = MOOD_VALUE[state.config.minimum_mood]
        minimum_mood_junior_year = MOOD_VALUE[state.config.minimum_mood_junior_year]
        turn = check_turn(state, screen)
        year = check_current_year(state, screen)
        criteria = check_criteria(state, screen)
        year_parts = year.split(" ")

        print("\n=======================================================================================\n")
        info(f"Year: {year}")
        info(f"Mood: {mood}")
        info(f"Turn: {turn}")
        info(f"Criteria: {criteria}")
        print("\n=======================================================================================\n")

        # URA SCENARIO
        if year == "Finale Season" and turn == "Race Day":
            info("URA Finale")
            if state.config.skill.is_auto_buy_skill:
                auto_buy_skill(state, screen)
            ura(state, screen)

            race_prep(state)
            sleep(1)
            after_race(state)
            continue

        # If calendar is race day, do race
        if turn == "Race Day" and year != "Finale Season":
            info("Race Day.")
            if state.config.skill.is_auto_buy_skill and year_parts[0] != "Junior":
                auto_buy_skill(state, screen)
            race_day(state)
            continue

        # Mood check
        if year_parts[0] == "Junior":
            mood_check = minimum_mood_junior_year
        else:
            mood_check = minimum_mood
        if mood_index < mood_check:
            if skipped_infirmary:
                info("Since we skipped infirmary due to energy, check full stats for statuses.")
                if click(state, img="assets/buttons/full_stats.png"):
                    sleep(0.5)
                    conditions, total_severity = check_status_effects(state)
                    click(state, img="assets/buttons/close_btn.png")
                    if total_severity > 1:
                        info("Severe condition found, visiting infirmary even though we will waste some energy.")
                        click_box(boxes=matches["infirmary"][0])
                        continue
                else:
                    warning("Coulnd't find full stats button.")
            else:
                info("Mood is low, trying recreation to increase mood")
                do_recreation(state)
                continue

        # If Prioritize G1 Race is true, check G1 race every turn
        if (
            state.config.prioritize_g1_race
            and "Pre-Debut" not in year
            and len(year_parts) > 3
            and year_parts[3] not in ["Jul", "Aug"]
        ):
            race_done = False
            for race in state.config.race_schedule:
                if race.year in year and race.date in year:
                    debug(f"Race now, {race.name}, {race.year} {race.date}")
                    if do_race(state, race=race.name):
                        race_done = True
                        break
                    else:
                        click(
                            state,
                            img="assets/buttons/back_btn.png",
                            text=f"{race.name} race not found. Proceeding to training.",
                        )
                        sleep(0.5)
            if race_done:
                continue

        # Check if we need to race for goal
        if "Achieved" not in criteria:
            if not state.memo.aptitudes:
                sleep(0.1)
                if click(state, img="assets/buttons/full_stats.png"):
                    sleep(0.5)
                    check_aptitudes(state)
                    click(state, img="assets/buttons/close_btn.png")
            keywords = ("fan", "Maiden", "Progress")

            prioritize_g1, race_name = decide_race_for_goal(state, year, turn, criteria, keywords)
            info(f"prioritize_g1: {prioritize_g1}, race_name: {race_name}")
            if race_name:
                if race_name == "any":
                    race_found = do_race(state, race=None)
                else:
                    race_found = do_race(state, race=race_name)
                if race_found:
                    continue
                else:
                    # If there is no race matching to aptitude, go back and do training instead
                    click(state, img="assets/buttons/back_btn.png", text="Proceeding to training.")
                    sleep(0.5)

        # Check training button
        if not go_to_training(state):
            debug("Training button is not found.")
            continue

        # Last, do training
        sleep(0.5)
        results_training = check_training(state)

        best_training = do_something(state, results_training)
        if best_training:
            go_to_training(state)
            sleep(0.5)
            do_train(state, best_training)
        else:
            do_rest(state, energy_level)
        sleep(1)

import re

import cv2
from rapidfuzz import fuzz

from core.data.config import EventChoice
from core.global_state import GlobalState
from core.ocr import extract_text
from utils.log import debug
from utils.screenshot import ensure_screenshot


def event_choice(state: GlobalState, event_name):
    threshold = 0.8
    choice = 0

    if not event_name:
        return choice

    best_event_name, similarity = find_best_match(event_name, state.config.event.event_choices)
    debug(f"Best event name match: {best_event_name}, similarity: {similarity}")

    if similarity >= threshold:
        events = next(
            (e for e in state.config.event.event_choices if e.event_name == best_event_name),
            None,  # fallback
        )
        debug(f"Event found: {event_name} has {similarity * 100:.2f}% similarity with {events.event_name}")
        debug(f"event name: {events.event_name}, chosen: {events.chosen}")
        choice = events.chosen
        return choice
    else:
        debug(f"No event found, {event_name} has {similarity * 100:.2f}% similarity with {best_event_name}")
        return choice


def get_event_name(state: GlobalState, existing_screen=None):
    existing_screen = ensure_screenshot(state, state.data.region.EVENT_NAME_REGION, existing_screen)
    # Original implementation bumped the contrast here to make OCR more reliable
    existing_screen = cv2.convertScaleAbs(existing_screen, alpha=1.5, beta=0)
    text = extract_text(existing_screen)
    debug(f"Event name: {text}")
    return text


def find_best_match(text: str, event_list: list[EventChoice]) -> tuple[str, float]:
    """Find the best matching skill and similarity score"""
    if not text or not event_list:
        return "", 0.0

    best_match = ""
    best_similarity = 0.0

    for event in event_list:
        event_name = event.event_name
        clean_text = re.sub(r"\s*\((?!Year 2\))[^\)]*\)", "", event_name).strip()  # remove parentheses
        clean_text = re.sub(r"[^\x00-\x7F]", "", clean_text)  # remove non-ASCII
        similarity = fuzz.token_sort_ratio(clean_text.lower(), text.lower()) / 100
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = event_name

    return best_match, best_similarity

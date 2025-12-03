"""Fancy mouse movement and clicks."""

import pyautogui

from core.data.regions import Position


def move_to(x: int, y: int, duration: float = 0.25) -> None:
    """Move the mouse to the given (x, y) coordinates.

    TODO: Make this less obvious xd. We can use bezier curves or something.
    Consider moving in small increments with random offsets. Since many cheaper
    mice have a polling rate of 125Hz (8ms), moving in small steps with slight delays
    can simulate more natural movement.
    """
    # current position is pyautogui.position()
    pyautogui.moveTo(x, y, duration=duration)


def move_to_position(pos: Position, duration: float = 0.25) -> None:
    move_to(pos.x, pos.y, duration=duration)


def move_to_center_of_bounding_box(box: tuple[int, int, int, int], duration: float = 0.25) -> None:
    """Move the mouse to the center of the given bounding box."""
    left, top, right, bottom = box
    center = (left + (right - left) // 2, top + (bottom - top) // 2)
    move_to(center[0], center[1], duration=duration)


def move_to_center_of_box(box: tuple[int, int, int, int], duration: float = 0.25) -> None:
    """Move the mouse to the center of the given box."""
    x, y, w, h = box
    center = (x + w // 2, y + h // 2)
    move_to(center[0], center[1], duration=duration)

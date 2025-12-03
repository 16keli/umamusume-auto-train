from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from core.state import GlobalState

from core.data.regions import Region


def ensure_screenshot(state: GlobalState, region: tuple[int, int, int, int] | None = None, existing_screen=None):
    if existing_screen is None:
        return state.screenshot(region=region)

    if region:
        return crop_image(existing_screen, region)
    return existing_screen


def adjust_position_for_region(
    position: tuple[int, int],
    region: Region | tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    """Adjusts position to account for any offset from the region."""
    if region is None:
        return position
    left, top = position
    if isinstance(region, Region):
        region = region.to_tuple()
    return (left + region[0], top + region[1])


def adjust_box_for_region(
    box: tuple[int, int, int, int], region: Region | tuple[int, int, int, int] | None = None
) -> tuple[int, int, int, int]:
    """Adjusts box to account for any offset from the region."""
    if region is None:
        return box
    left, top, width, height = box
    if isinstance(region, Region):
        region = region.to_tuple()
    return (left + region[0], top + region[1], width, height)


def adjust_bounds_for_region(
    bounds: tuple[int, int, int, int], region: Region | tuple[int, int, int, int] | None = None
) -> tuple[int, int, int, int]:
    """Adjusts bounds to account for any offset from the region."""
    if region is None:
        return bounds
    x1, y1, x2, y2 = bounds
    if isinstance(region, Region):
        region = region.to_tuple()
    return (x1 + region[0], y1 + region[1], x2 + region[0], y2 + region[1])


def apply_offset_to_tuple(
    bounds: tuple[int, int, int, int], region: Region | tuple[int, int, int, int] | None = None
) -> tuple[int, int, int, int]:
    """Applies a basic offset from the region."""
    if region is None:
        return bounds
    x1, y1, x2, y2 = bounds
    if isinstance(region, Region):
        region = region.to_tuple()
    return (x1 + region[0], y1 + region[1], x2 + region[2], y2 + region[3])


def box_to_bounds(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, width, height = box
    right = left + width
    bottom = top + height
    return (left, top, right, bottom)


def crop_image(img: np.ndarray, box: Region | tuple[int, int, int, int]) -> np.ndarray:
    if isinstance(box, Region):
        box = box.to_box()
    left, top, width, height = box
    right = left + width
    bottom = top + height
    return img[top:bottom, left:right]

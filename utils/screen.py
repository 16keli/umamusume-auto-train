_RESOLUTIONS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


_BASELINE_HEIGHT = 2160  # assets are assumed to be authored for 4k baseline


def screen_height_to_scale(screen_height: int | str) -> float:
    # determine target height
    if isinstance(screen_height, int):
        target_height = int(screen_height)
    else:
        screen_key = str(screen_height).strip().lower()
        if screen_key in _RESOLUTIONS:
            _, target_height = _RESOLUTIONS[screen_key]
        else:
            # allow numeric strings like "1080" or "1080p"
            if screen_key.endswith("p") and screen_key[:-1].isdigit():
                target_height = int(screen_key[:-1])
            elif screen_key.isdigit():
                target_height = int(screen_key)
            else:
                raise ValueError(
                    f"Unsupported screen resolution: {screen_height!r}. "
                    "Provide an integer pixel height (e.g. 1080), a string like '1080p', "
                    f"or one of the supported keys: {', '.join(_RESOLUTIONS)}"
                )

    if target_height <= 0:
        raise ValueError(f"Invalid target height: {target_height}. Must be a positive integer.")

    scale = target_height / _BASELINE_HEIGHT

    return scale


def scale_value_for_screen_height(value: int, screen_height: int | str) -> int:
    scale = screen_height_to_scale(screen_height)
    return int(round(value * scale))


def box_to_bounds(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, width, height = box
    right = left + width
    bottom = top + height
    return (left, top, right, bottom)

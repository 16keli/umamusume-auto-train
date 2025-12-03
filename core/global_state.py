from __future__ import annotations

import platform
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict

if platform.system() == "Windows":
    from dxcam_cpp import DXCamera  # pyright: ignore[reportMissingImports]
else:
    from dxcam import DXCamera

import numpy as np
from pygetwindow import BaseWindow

from core.data.config import ConfigStruct
from core.data.races import Race, RaceYear
from core.data.regions import Region, ScreenRegions
from core.data.skills import Skill
from utils.screen import box_to_bounds
from utils.screenshot import crop_image

"""
core/global_state.py

A class that holds global state for the application:
- assets: a dictionary of loaded assets (images, templates, etc.)
- game_window: hook to the game window
- config: application configuration settings
- cam: DXCamera instance for screen capturing
"""


@dataclass
class GlobalData:
    """Singleton that stores global data."""

    race: list[RaceYear]
    region: ScreenRegions
    skill: list[Skill]

    @cached_property
    def races_by_turn(self) -> dict[str, list[Race]]:
        holding_dict = defaultdict(list)
        for year in self.race:
            for race in year.races:
                holding_dict[f"{year.year} {race.date}"].append(race)
        return holding_dict


def load_global_data(screen_height: int | str = 1080, delta_x: int = 0, delta_y: int = 0) -> GlobalData:
    """Load and return the global data singleton."""
    from core.data.races import load_races
    from core.data.regions import load_regions
    from core.data.skills import load_skills

    return GlobalData(
        race=load_races(),
        region=load_regions(screen_height=screen_height, delta_x=delta_x, delta_y=delta_y),
        skill=load_skills(),
    )


@dataclass
class BotState:
    """Holds runtime state for the bot."""

    stop_event = threading.Event()
    is_bot_running = False
    bot_thread = None
    bot_lock = threading.Lock()


@dataclass
class Memoize:
    """State that can be memoized during bot execution."""

    preferred_position_set: bool = False
    previous_right_bar_match: list = field(default_factory=list)
    aptitudes: dict[str, str] = field(default_factory=dict)


@dataclass
class GlobalState:
    """
    Singleton that stores global application state:
      - assets: Dict[str, Any]
      - window_info: BaseWindow
      - config: ConfigStruct
      - cam: DXCamera

    Thread-safe for simple concurrent access.

    Funny helper functions too.
    """

    assets: Dict[str, Any]
    data: GlobalData
    game_window: BaseWindow
    config: ConfigStruct
    cam: DXCamera

    previous_frame: np.ndarray = field(default_factory=list)
    memo: Memoize = field(default_factory=Memoize)
    bot: BotState = field(default_factory=BotState)

    @cached_property
    def window_bounds(self) -> tuple[int, int, int, int]:
        return box_to_bounds(self.game_window.box)

    def screenshot(self, region: Region | tuple[int, int, int, int] | None = None) -> np.ndarray:
        """Take a screenshot of the game window or a specific region."""
        region = region or self.window_bounds
        screen = self.cam.grab(self.window_bounds)
        # DXCam will return None if no change since the previous frame
        if screen is None:
            screen = self.previous_frame
            if screen.size == 0:
                raise RuntimeError("No previous frame ever?")
            # warning("Screenshot called and returned None, no change detected.")
        else:
            self.previous_frame = screen

        return crop_image(screen, region) if region is not self.window_bounds else screen

    def asset_by_path(self, path: str) -> Any:
        """Get an asset by its path."""
        current = self.assets
        parts = path.split("/")
        for part in parts:
            # Skip the 'assets' root
            if part == "assets":
                continue
            if part not in current:
                raise KeyError(f"Asset not found: {part} in {path}")
            current = current[part]
        return current

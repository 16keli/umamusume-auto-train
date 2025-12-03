from enum import Enum
from functools import cached_property

import msgspec


class Mood(Enum):
    AWFUL = "AWFUL"
    BAD = "BAD"
    NORMAL = "NORMAL"
    GOOD = "GOOD"
    GREAT = "GREAT"
    UNKNOWN = "UNKNOWN"


MOOD_VALUE = {
    Mood.UNKNOWN: 0,
    Mood.AWFUL: 0,
    Mood.BAD: 1,
    Mood.NORMAL: 2,
    Mood.GOOD: 3,
    Mood.GREAT: 4,
}


class RacePosition(Enum):
    FRONT = "front"
    PACE = "pace"
    LATE = "late"
    END = "end"


class PriorityWeight(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    NONE = 0


class SkillConfig(msgspec.Struct):
    is_auto_buy_skill: bool
    skill_pts_check: int
    skill_list: list[str]


class EventChoice(msgspec.Struct):
    event_name: str
    character_name: str
    chosen: int


class EventConfig(msgspec.Struct):
    use_optimal_event_choice: bool
    event_choices: list[EventChoice]


class RaceInfo(msgspec.Struct):
    name: str
    year: str
    date: str


class ConfigStruct(msgspec.Struct, dict=True):
    priority_stat: list[str]
    priority_weights: list[float]
    minimum_mood: Mood
    minimum_mood_junior_year: Mood
    maximum_failure: int
    prioritize_g1_race: bool
    cancel_consecutive_race: bool
    stat_caps: dict[str, int]
    skill: SkillConfig
    skip_training_energy: int
    never_rest_energy: int
    skip_infirmary_unless_missing_energy: int
    priority_weight: str
    preferred_position: RacePosition
    enable_positions_by_race: bool
    positions_by_race: dict[str, RacePosition]
    position_selection_enabled: bool
    sleep_time_multiplier: float
    window_name: str
    race_schedule: list[RaceInfo]
    config_name: str
    event: EventConfig

    @cached_property
    def priority_effects_mapping(self) -> dict[str, float]:
        # TODO: Figure out what the intent of this was supposed to be
        return {i: v for i, v in enumerate(self.priority_weights)}


def load_config():
    with open("config.json", "r", encoding="utf-8") as file:
        return msgspec.json.decode(file.read(), type=ConfigStruct)

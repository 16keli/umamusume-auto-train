import msgspec

from utils.screen import screen_height_to_scale


class Region(msgspec.Struct):
    """A rectangular region on the screen.

    (x1, y1) is the top-left corner
    (x2, y2) is the bottom-right corner
    """

    x1: int
    y1: int
    x2: int
    y2: int

    def scale(self, factor: float) -> "Region":
        """Scale the region by a factor."""
        return Region(
            x1=int(self.x1 * factor),
            y1=int(self.y1 * factor),
            x2=int(self.x2 * factor),
            y2=int(self.y2 * factor),
        )

    def translate(self, delta_x: int, delta_y: int) -> "Region":
        """Translate the region by delta_x and delta_y."""
        return Region(
            x1=self.x1 + delta_x,
            y1=self.y1 + delta_y,
            x2=self.x2 + delta_x,
            y2=self.y2 + delta_y,
        )

    def to_tuple(self) -> tuple[int, int, int, int]:
        """Convert the region to a tuple (x1, y1, x2, y2)."""
        return (self.x1, self.y1, self.x2, self.y2)

    def to_box(self) -> tuple[int, int, int, int]:
        """Convert the region to a box (x, y, width, height)."""
        return (self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1)


class Position(msgspec.Struct):
    """A position on the screen."""

    x: int
    y: int

    def scale(self, factor: float) -> "Position":
        """Scale the position by a factor."""
        return Position(
            x=int(self.x * factor),
            y=int(self.y * factor),
        )

    def translate(self, delta_x: int, delta_y: int) -> "Position":
        """Translate the position by delta_x and delta_y."""
        return Position(
            x=self.x + delta_x,
            y=self.y + delta_y,
        )


class ScreenRegions(msgspec.Struct):
    MOOD_REGION: Region
    TURN_REGION: Region
    FAILURE_REGION: Region
    YEAR_REGION: Region
    CRITERIA_REGION: Region
    EVENT_NAME_REGION: Region
    SKILL_PTS_REGION: Region
    SKIP_BTN_BIG_REGION_LANDSCAPE: Region
    SCREEN_BOTTOM_REGION: Region
    SCREEN_MIDDLE_REGION: Region
    SCREEN_TOP_REGION: Region
    RACE_INFO_TEXT_REGION: Region
    RACE_LIST_BOX_REGION: Region
    FULL_STATS_STATUS_REGION: Region
    FULL_STATS_APTITUDE_REGION: Region
    SKILL_NAME_OFFSET: Region
    SPD_STAT_REGION: Region
    STA_STAT_REGION: Region
    PWR_STAT_REGION: Region
    GUTS_STAT_REGION: Region
    WIT_STAT_REGION: Region
    SUPPORT_CARD_ICON_BBOX: Region
    ENERGY_BBOX: Region
    RACE_BUTTON_IN_RACE_BBOX_LANDSCAPE: Region
    GAME_SCREEN_REGION: Region

    SCROLLING_SELECTION_MOUSE_POS: Position
    SKILL_SCROLL_BOTTOM_MOUSE_POS: Position
    RACE_SCROLL_BOTTOM_MOUSE_POS: Position

    def scale_all(self, factor: float) -> "ScreenRegions":
        """Scale all regions by a factor."""
        scaled_fields = {field: getattr(self, field).scale(factor) for field in self.__struct_fields__}
        return ScreenRegions(**scaled_fields)

    def translate_all(self, delta_x: int, delta_y: int) -> "ScreenRegions":
        """Translate all regions by delta_x and delta_y."""
        translated_fields = {
            field: getattr(self, field).translate(delta_x, delta_y) for field in self.__struct_fields__
        }
        return ScreenRegions(**translated_fields)


def load_regions(screen_height: int | str = 1080, delta_x: int = 0, delta_y: int = 0) -> ScreenRegions:
    scale = screen_height_to_scale(screen_height)
    with open("data/regions.json", "r", encoding="utf-8") as file:
        regions_baseline = msgspec.json.decode(file.read(), type=ScreenRegions)

    if scale != 1.0:
        regions_baseline = regions_baseline.scale_all(scale)

    if delta_x != 0 or delta_y != 0:
        regions_baseline = regions_baseline.translate_all(delta_x, delta_y)

    return regions_baseline

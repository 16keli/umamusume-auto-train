import msgspec


class RaceDistance(msgspec.Struct):
    type: str
    meters: int


class RaceFans(msgspec.Struct):
    required: int
    gained: int


class Race(msgspec.Struct):
    race: str
    date: str
    racetrack: str
    terrain: str
    distance: RaceDistance
    sparks: list[str]
    fans: RaceFans


class RaceYear(msgspec.Struct):
    year: str
    races: list[Race]


def load_races():
    with open("data/races.json", "r", encoding="utf-8") as file:
        return msgspec.json.decode(file.read(), type=list[RaceYear])

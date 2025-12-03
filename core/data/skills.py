import msgspec


class Skill(msgspec.Struct):
    name: str
    description: str


def load_skills():
    with open("data/skills.json", "r", encoding="utf-8") as file:
        return msgspec.json.decode(file.read(), type=list[Skill])

"""D138 변이 - 쓰는 단계 9개 · 쓰는 단계 점검 13개 · 독립 검토 2개 (약화 14 · 안전 10 · 경쟁 0). 규약은 src/codeproof_ai/corpus/mutants.py."""

_DECO = "@dataclasses.dataclass(frozen=True, slots=True)\n"
_CLASS = _DECO + "class Limits:\n    projects: int\n    seats: int\n"
_RETURN = "    return plan.value\n"

WEAKENED: dict[str, list[tuple[str, str]]] = {
    "[고정] frozen 이 아님 (twin)": [(_DECO, "@dataclasses.dataclass(slots=True)\n")],
    "[고정] __slots__ 만 둔 평범한 클래스": [
        (_CLASS, "class Limits:\n    __slots__ = (\"projects\", \"seats\")\n\n    def __init__(self, projects: int, seats: int) -> None:\n"
                 "        self.projects = projects\n        self.seats = seats\n"),
    ],
    "[값] TEAM 이 FREE 와 같은 값 - Enum 이 별칭으로 접는다": [
        ("    TEAM = Limits(projects=50, seats=10)\n", "    TEAM = Limits(projects=3, seats=1)\n"),
    ],
    "[값] TEAM 좌석 11": [("    TEAM = Limits(projects=50, seats=10)\n", "    TEAM = Limits(projects=50, seats=11)\n")],
    # 쓰는 단계 점검 - 원래 증명이 놓치던 약화
    '[삭제] seats 는 지워짐 - projects 만 property · __delattr__ 없음': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        object.__setattr__(self, "_projects", projects)\n        object.__setattr__(self, "seats", seats)\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    def __setattr__(self, name: str, value: object) -> None:\n        raise AttributeError(f"{name} is read-only")\n')],
    '[삭제] 지우기 막는 이름 목록에서 seats 를 빠뜨림': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', '@dataclasses.dataclass(slots=True)\nclass Limits:\n    projects: int\n    seats: int\n\n    def __setattr__(self, name: str, value: object) -> None:\n        if hasattr(self, name):\n            raise AttributeError(f"{name} is read-only")\n        object.__setattr__(self, name, value)\n\n    def __delattr__(self, name: str) -> None:\n        if name == "projects":\n            raise AttributeError(f"cannot delete {name}")\n        object.__delattr__(self, name)\n')],
    # 쓰는 단계 점검 - 축마다 그 축으로만 잡히는 약화
    '[고정] seats 만 읽기 전용 · 지우기 막음 - projects 대입은 받음': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        self.projects = projects\n        self._seats = seats\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n\n    def __delattr__(self, name: str) -> None:\n        raise AttributeError(f"cannot delete {name}")\n')],
    '[고정] seats setter 가 1 미만만 거절 - 늘리기는 받음': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        self._projects = projects\n        self._seats = seats\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n\n    @seats.setter\n    def seats(self, value: int) -> None:\n        if value < 1:\n            raise ValueError("a plan has at least one seat")\n        self._seats = value\n')],
    '[고정] 한 번만 쓰는 __setattr__ - __delattr__ 를 빠뜨림': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', '@dataclasses.dataclass(slots=True)\nclass Limits:\n    projects: int\n    seats: int\n\n    def __setattr__(self, name: str, value: object) -> None:\n        if hasattr(self, name):\n            raise AttributeError(f"{name} is read-only")\n        object.__setattr__(self, name, value)\n')],
    '[고정] seats setter 가 늘리기만 거절 - 줄이기는 받음': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        self._projects = projects\n        self._seats = seats\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n\n    @seats.setter\n    def seats(self, value: int) -> None:\n        if value > self._seats:\n            raise ValueError("a plan cannot raise its own seat limit")\n        self._seats = value\n')],
    '[고정] 필드는 막고 덮어쓰기 속성 projects_override 는 받음 (탐침 이름에 맞춘 인위적 변이)': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats", "projects_override")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        object.__setattr__(self, "_projects", projects)\n        object.__setattr__(self, "_seats", seats)\n\n    @property\n    def projects(self) -> int:\n        return getattr(self, "projects_override", self._projects)\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n\n    def __setattr__(self, name: str, value: object) -> None:\n        if name != "projects_override":\n            raise AttributeError(f"{name} is read-only")\n        object.__setattr__(self, name, value)\n\n    def __delattr__(self, name: str) -> None:\n        raise AttributeError(f"cannot delete {name}")\n')],
    '[고정] TEAM 만 frozen 이 아닌 다른 클래스': [('class Plan(enum.Enum):\n', '@dataclasses.dataclass(slots=True)\nclass _TeamLimits:\n    projects: int\n    seats: int\n\n\nclass Plan(enum.Enum):\n'), ('    TEAM = Limits(projects=50, seats=10)\n', '    TEAM = _TeamLimits(projects=50, seats=10)\n')],
    # 독립 검토 - 원래 증명이 놓치던 약화
    '[대입] projects 에 범위를 보는 setter - 0~100 안의 값은 받아 요금제 한도가 바뀜': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        self._projects = projects\n        self._seats = seats\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    @projects.setter\n    def projects(self, value: int) -> None:\n        if not 0 <= value <= 100:\n            raise ValueError("projects 는 0~100 이다")\n        self._projects = value\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n')],
    '[대입] projects 는 늘리기만 거절 - 줄이기는 받아 요금제 한도가 바뀜': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        self._projects = projects\n        self._seats = seats\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    @projects.setter\n    def projects(self, value: int) -> None:\n        if value > self._projects:\n            raise ValueError("한도는 늘릴 수 없다")\n        self._projects = value\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n')],
}

SAFE: dict[str, list[tuple[str, str]]] = {
    "slots 없이 frozen (안전)": [(_DECO, "@dataclasses.dataclass(frozen=True)\n")],
    "NamedTuple (안전)": [
        (_CLASS, "class Limits(typing.NamedTuple):\n    projects: int\n    seats: int\n"),
        ("import enum\n", "import enum\nimport typing\n"),
    ],
    "가변이지만 부를 때마다 사본 (안전)": [(_DECO, "@dataclasses.dataclass(slots=True)\n"), (_RETURN, "    return dataclasses.replace(plan.value)\n")],
    "frozen + eq=False (안전)": [(_DECO, "@dataclasses.dataclass(frozen=True, slots=True, eq=False)\n")],
    "값을 튜플로 두고 부를 때 만듦 (안전)": [
        ("    FREE = Limits(projects=3, seats=1)\n    TEAM = Limits(projects=50, seats=10)\n", "    FREE = (3, 1)\n    TEAM = (50, 10)\n"),
        (_RETURN, "    return Limits(*plan.value)\n"),
    ],
    # 쓰는 단계 점검 - 주장이 정하지 않은 것을 바꾼 안전한 변형
    '읽기 전용 property · __slots__ · TypeError 로 거절 (안전)': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'class Limits:\n    __slots__ = ("_projects", "_seats")\n\n    def __init__(self, projects: int, seats: int) -> None:\n        object.__setattr__(self, "_projects", projects)\n        object.__setattr__(self, "_seats", seats)\n\n    @property\n    def projects(self) -> int:\n        return self._projects\n\n    @property\n    def seats(self) -> int:\n        return self._seats\n\n    def __setattr__(self, name: str, value: object) -> None:\n        raise TypeError("Limits is read-only")\n\n    def __delattr__(self, name: str) -> None:\n        raise TypeError("Limits is read-only")\n')],
    'from dataclasses import dataclass 꼴 (안전)': [('import dataclasses\n', 'from dataclasses import dataclass\n'), ('@dataclasses.dataclass(frozen=True, slots=True)\n', '@dataclass(frozen=True, slots=True)\n')],
    'collections.namedtuple (안전)': [('@dataclasses.dataclass(frozen=True, slots=True)\nclass Limits:\n    projects: int\n    seats: int\n', 'Limits = collections.namedtuple("Limits", ["projects", "seats"])\n'), ('import enum\n', 'import collections\nimport enum\n')],
    'limits_for 가 copy.copy 를 돌려줌 (안전)': [('    return plan.value\n', '    return copy.copy(plan.value)\n'), ('import dataclasses\n', 'import copy\nimport dataclasses\n')],
    '한도를 MappingProxyType 표에서 (안전)': [('    FREE = Limits(projects=3, seats=1)\n    TEAM = Limits(projects=50, seats=10)\n', '    FREE = "free"\n    TEAM = "team"\n'), ('\n\ndef limits_for(plan: Plan) -> Limits:\n', '\n\n_TABLE = types.MappingProxyType(\n    {Plan.FREE: Limits(projects=3, seats=1), Plan.TEAM: Limits(projects=50, seats=10)}\n)\n\n\ndef limits_for(plan: Plan) -> Limits:\n'), ('    return plan.value\n', '    return _TABLE[plan]\n'), ('import enum\n', 'import enum\nimport types\n')],
}

RACY: dict[str, list[tuple[str, str]]] = {}

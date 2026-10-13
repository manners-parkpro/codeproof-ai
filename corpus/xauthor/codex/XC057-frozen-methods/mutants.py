"""불변화의 축을 검증한다 - 원본 분리와 변경 경로별 약화 및 안전한 대안을 실행한다."""

PREFIX = 'BOOTSTRAP = {"GET", "HEAD", "OPTIONS"}'
GUARD = "METHODS = frozenset(BOOTSTRAP)"

FACADE = '''class _Closed(Set):
    def __init__(self, values):
        self._items = set(values)

    def __contains__(self, value):
        return value in self._items

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def copy(self):
        return type(self)(self)

    def union(self, other):
        return type(self)(self._items.union(other))

    def intersection(self, other):
        return type(self)(self._items.intersection(other))

    def difference(self, other):
        return type(self)(self._items.difference(other))

    def symmetric_difference(self, other):
        return type(self)(self._items.symmetric_difference(other))

'''


def facade(extra="", source=FACADE):
    return [
        (PREFIX, source + extra + "\n" + PREFIX),
        (GUARD, "METHODS = _Closed(BOOTSTRAP)"),
    ]


WEAKENED = {
    "공개 집합: 복사했지만 가변 set": [(GUARD, "METHODS = set(BOOTSTRAP)")],
    "원본 분리: 원본 자체를 공유": [(GUARD, "METHODS = BOOTSTRAP")],
    "원본 분리: 읽기 전용 외피가 원본을 참조": facade(
        source=FACADE.replace("self._items = set(values)", "self._items = values")
    ),
    "새 반환값: 초기 원본을 노출": [
        ("    return METHODS", "    return BOOTSTRAP")
    ],
    "판정 경로: 초기 원본을 읽음": [
        ("return method in METHODS", "return method in BOOTSTRAP")
    ],
}

for name in (
    "add", "discard", "remove", "update", "intersection_update",
    "difference_update", "symmetric_difference_update", "pop", "clear",
):
    WEAKENED["공개 변경: " + name + "만 차단 누락"] = facade(
        f"    def {name}(self, *args):\n"
        f"        return self._items.{name}(*args)\n"
    )

for name in ("__ior__", "__iand__", "__isub__", "__ixor__"):
    WEAKENED["제자리 연산: " + name + "만 차단 누락"] = facade(
        f"    def {name}(self, other):\n"
        f"        self._items.{name}(other)\n"
        "        return self\n"
    )

for name in (
    "copy", "union", "intersection", "difference", "symmetric_difference",
    "__or__", "__and__", "__sub__", "__xor__",
    "__ror__", "__rand__", "__rsub__", "__rxor__",
):
    if name == "copy":
        source = FACADE.replace(
            "return type(self)(self)", "return self._items"
        )
        edits = facade(source=source)
    elif not name.startswith("__"):
        source = FACADE.replace(
            f"return type(self)(self._items.{name}(other))",
            "return self._items",
        )
        edits = facade(source=source)
    else:
        edits = facade(
            f"    def {name}(self, other):\n"
            "        return self._items\n"
        )
    WEAKENED["파생 결과: " + name + "에서 저장소 유출"] = edits

for label, predicate in (
    ("빈 문자열", 'value == ""'),
    ("큰 문자열", "len(value) > 10000"),
    ("일반 하위 타입", "type(value) is not str"),
):
    WEAKENED["원소 경계: " + label + "에만 변경 허용"] = facade(
        "    def add(self, value):\n"
        f"        if {predicate}:\n"
        "            self._items.add(value)\n"
    )

WEAKENED["동기 예외: add가 변경 뒤 거절"] = facade(
    "    def add(self, value):\n"
    "        self._items.add(value)\n"
    "        raise ValueError(value)\n"
)
WEAKENED["동기 예외: 제자리 연산이 변경 뒤 거절"] = facade(
    "    def __ior__(self, other):\n"
    "        self._items.update(other)\n"
    "        raise ValueError(other)\n"
)
WEAKENED["동기 예외: 복사 호출이 변경 뒤 거절"] = facade(
    source=FACADE.replace(
        "return type(self)(self)",
        'self._items.clear()\n        raise ValueError("copy")',
    )
)

SAFE = {
    "원본 복사를 거친 불변 집합": [
        (GUARD, "METHODS = frozenset(BOOTSTRAP.copy())")
    ],
    "초기 원소 순서 변경": [
        (GUARD, "METHODS = frozenset(sorted(BOOTSTRAP, reverse=True))")
    ],
    "독립적인 가변 반환값": [
        ("    return METHODS", "    return set(METHODS)")
    ],
    "멤버십을 동등성 비교로 구현": [
        ("return method in METHODS",
         "return any(method == candidate for candidate in METHODS)")
    ],
    "공개 변경 연산이 없는 복사 외피": facade(),
    "변경 거절 예외 타입 변경": facade(
        "    def __getattr__(self, name):\n"
        "        raise ValueError(name)\n"
    ),
    "frozenset 일반 하위 타입": [
        (PREFIX, "class _Frozen(frozenset):\n    pass\n\n" + PREFIX),
        (GUARD, "METHODS = _Frozen(BOOTSTRAP)"),
    ],
}

RACY = {}

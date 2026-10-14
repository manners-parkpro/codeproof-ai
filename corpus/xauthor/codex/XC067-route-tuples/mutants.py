"""주장 축별 변이 - 원본 분리, 중첩 불변성, 변경 수단과 의미 경계를 대조한다."""

GUARD = "ROUTES = tuple(tuple(row) for row in BOOTSTRAP)"

WEAKENED = {
    "원본 표 별칭": [(GUARD, "ROUTES = BOOTSTRAP")],
    "바깥 표만 고정": [(GUARD, "ROUTES = tuple(BOOTSTRAP)")],
    "행만 고정": [(GUARD, "ROUTES = [tuple(row) for row in BOOTSTRAP]")],
    "행 복사만 수행": [(GUARD, "ROUTES = tuple(row[:] for row in BOOTSTRAP)")],
    "첫 행만 공유": [(GUARD, "ROUTES = tuple(row if i == 0 else tuple(row) for i, row in enumerate(BOOTSTRAP))")],
    "중간 행만 공유": [(GUARD, "ROUTES = tuple(row if i == 1 else tuple(row) for i, row in enumerate(BOOTSTRAP))")],
    "끝 행만 공유": [(GUARD, "ROUTES = tuple(row if i == 2 else tuple(row) for i, row in enumerate(BOOTSTRAP))")],
    "원본 변경 뒤 재생성": [("    return ROUTES", "    return tuple(tuple(row) for row in BOOTSTRAP)")],
    "반환 복사본을 캐시해 노출": [
        (GUARD, GUARD + "\nEXPOSED = [list(row) for row in ROUTES]"),
        ("    return ROUTES", "    return EXPOSED"),
    ],
    "경계 제외": [("load >= threshold", "load > threshold")],
    "극단 정수 축소": [("reversed(ROUTES):", "reversed(ROUTES):\n        load = min(79, load)")],
    "하위 타입 거절": [("    for threshold, queue", "    if type(load) is not int:\n        raise TypeError(load)\n    for threshold, queue")],
}

METHODS = (
    "__setitem__", "__delitem__", "append", "extend", "insert", "pop",
    "remove", "clear", "reverse", "sort", "__iadd__", "__imul__",
)

for method in METHODS:
    definitions = "\n".join(
        "    " + name + " = " + ("list." + name if name == method else "_deny")
        for name in METHODS
    )
    replacement = (
        "def _deny(*args, **kwargs):\n    raise TypeError()\n\n"
        "class SealedRow(list):\n" + definitions + "\n\n"
        "ROUTES = tuple(SealedRow(row) for row in BOOTSTRAP)"
    )
    WEAKENED["행 변경 누락 " + method] = [(GUARD, replacement)]

for name, condition in {
    "단일 항목": "not isinstance(key, slice)",
    "연속 슬라이스": "isinstance(key, slice) and key.step is None",
    "확장 슬라이스": "isinstance(key, slice) and key.step == 2",
    "큰 정수 대입": "not isinstance(key, slice) and isinstance(value, int) and value > 2**512",
    "bool 대입": "not isinstance(key, slice) and isinstance(value, bool)",
}.items():
    definitions = "\n".join("    " + method + " = _deny" for method in METHODS)
    replacement = (
        "def _deny(*args, **kwargs):\n    raise ValueError()\n\n"
        "class SealedRow(list):\n" + definitions + "\n"
        "    def __setitem__(self, key, value):\n"
        "        if " + condition + ":\n"
        "            return list.__setitem__(self, key, value)\n"
        "        raise ValueError()\n\n"
        "ROUTES = tuple(SealedRow(row) for row in BOOTSTRAP)"
    )
    WEAKENED["대입 경로 누락 " + name] = [(GUARD, replacement)]

SAFE = {
    "map으로 중첩 동결": [(GUARD, "ROUTES = tuple(map(tuple, BOOTSTRAP))")],
    "원본을 먼저 깊은 복사": [(GUARD, "ROUTES = tuple(tuple(row[:]) for row in BOOTSTRAP[:])")],
    "행은 불변 bytes": [(GUARD, "ROUTES = tuple(bytes(row) for row in BOOTSTRAP)")],
    "행은 이름 붙인 tuple": [
        (GUARD, "from collections import namedtuple\nRow = namedtuple('Row', 'threshold queue')\nROUTES = tuple(Row(*row) for row in BOOTSTRAP)")
    ],
    "반환값은 매번 가변 깊은 복사": [("    return ROUTES", "    return [list(row) for row in ROUTES]")],
    "반환값은 매번 가변 얕은 복사": [("    return ROUTES", "    return list(ROUTES)")],
    "별도 구축 표": [(GUARD, "ROUTES = ((0, 3), (50, 2), (80, 1))")],
    "거절 예외 변경": [
        (GUARD, "class Row(tuple):\n    def __setitem__(self, key, value):\n        raise RuntimeError('sealed')\n    def __delitem__(self, key):\n        raise RuntimeError('sealed')\n\nROUTES = tuple(Row(row) for row in BOOTSTRAP)")
    ],
}

RACY = {}

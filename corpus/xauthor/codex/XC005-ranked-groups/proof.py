"""원본 보존과 양방향 격리 공격 - 입력 모양과 변경 수단을 교차한다."""

from enum import IntEnum
from types import ModuleType


class PlainList(list):
    pass


class PlainInt(int):
    pass


class Score(IntEnum):
    LOW = -3
    HIGH = 8


MARK = -(10**150 + 7)
SHAPES = (
    (),
    ((),),
    ((), ()),
    ((3, 1, 2),),
    ((8, 8, -3), (), (4, 0)),
    ((False, True, False), (Score.LOW, Score.HIGH)),
    ((PlainInt(2), PlainInt(-4)),),
    ((-(10**200), 10**200, 0),),
    tuple((i, -i) for i in range(257)),
    (tuple(range(257)),),
)
COUNTS = (-10**100, -1, 0, 1, 2, 256, 257, 10**100, False, True,
          Score.LOW, Score.HIGH, PlainInt(1))
OPERATIONS = (
    "outer_append", "outer_clear", "outer_reverse", "outer_slice",
    "inner_append", "inner_clear", "inner_reverse", "inner_slice",
)


def snapshot(groups):
    return tuple((id(group), tuple(group)) for group in groups)


def make_groups(shape, outer, inner, shared):
    groups = outer(inner(values) for values in shape)
    if shared and groups:
        groups.append(groups[0])
    return groups


def change(groups, operation, index):
    if operation == "outer_append":
        groups.append([MARK])
    elif operation == "outer_clear":
        groups.clear()
    elif operation == "outer_reverse":
        groups.reverse()
    elif operation == "outer_slice":
        groups[:] = [[MARK], []]
    elif operation == "inner_append":
        groups[index].append(MARK)
    elif operation == "inner_clear":
        groups[index].clear()
    elif operation == "inner_reverse":
        groups[index].reverse()
    elif operation == "inner_slice":
        groups[index][:] = [MARK]


def attack(mod: ModuleType) -> bool:
    for shape in SHAPES:
        for outer, inner in ((list, list), (PlainList, list),
                             (list, PlainList), (PlainList, PlainList)):
            for shared in (False, True):
                for count in COUNTS:
                    source = make_groups(shape, outer, inner, shared)
                    before = snapshot(source)
                    try:
                        result = mod.top_scores(source, count)
                    except Exception:
                        if snapshot(source) != before:
                            return True
                        if count < 0:
                            continue
                        raise
                    if snapshot(source) != before:
                        return True
                    for target in ("source", "result"):
                        size = len(source if target == "source" else result)
                        row_indices = sorted({0, size // 2, size - 1}) if size else ()
                        for operation in OPERATIONS:
                            indices = row_indices if operation.startswith("inner") else (0,)
                            for index in indices:
                                source = make_groups(shape, outer, inner, shared)
                                before = snapshot(source)
                                result = mod.top_scores(source, count)
                                if snapshot(source) != before:
                                    return True
                                victim = result if target == "source" else source
                                before = snapshot(victim)
                                change(source if target == "source" else result,
                                       operation, index)
                                if snapshot(victim) != before:
                                    return True
    return False

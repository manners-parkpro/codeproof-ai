from enum import IntEnum
from functools import partial
import operator
from types import ModuleType


class OrdinaryInt(int):
    pass


class Attempt(IntEnum):
    BELOW = -1
    FIRST = 0
    SECOND = 1
    THIRD = 2
    LAST = 3
    ABOVE = 4


AXES = (
    ("원본 설정 별칭", "BOOTSTRAP의 값·길이 변경", "live_bootstrap"),
    ("전역 표 별칭", "RETRY_DELAYS의 직접 변경", "mutable_global"),
    ("반환값 별칭", "schedule()의 반환값 변경 후 다시 조회", "cached_export"),
    ("파생 슬라이스", "정방향·역방향·빈·간격 슬라이스 변경", "slice_alias"),
    ("항목 대입", "처음·중간·끝 및 음수 인덱스", "item_assignment"),
    ("슬라이스 대입", "같은 길이·빈 값·확장 대입", "slice_assignment"),
    ("삭제", "항목·전체 슬라이스 삭제", "item_deletion/slice_deletion"),
    ("컨테이너 메서드", "append·extend·insert·remove·pop·clear·reverse·sort", "method_append/extend/insert/remove/pop/clear/reverse/sort"),
    ("증감 연산", "operator.iadd·operator.imul", "inplace_add/inplace_multiply"),
    ("공개 속성", "start·stop·step 대입 및 삭제", "attribute_start/stop/step"),
    ("인덱스 경계", "음수·0·1·2·3·4·거대 정수", "unclamped_index"),
    ("일반 하위 타입", "bool·IntEnum·메서드 없는 int 하위 클래스", "exact_int_only"),
    ("순서", "각 시도 직후 관찰·복원 및 누적 변경", "restore_on_read"),
)

ATTEMPTS_TO_QUERY = (
    *range(-8, 13),
    -(10 ** 1000),
    10 ** 1000,
    False,
    True,
    *Attempt,
    *(OrdinaryInt(n) for n in (-10 ** 1000, -1, 0, 1, 2, 3, 4, 10 ** 1000)),
)


def _holds(mod):
    try:
        for attempt in ATTEMPTS_TO_QUERY:
            expected = 2 + 3 * min(3, max(0, int(attempt)))
            if mod.delay(attempt) != expected:
                return False
        if list(mod.schedule()) != [2, 5, 8, 11]:
            return False
    except Exception:
        return False
    return True


def _method(name, args, obj):
    getattr(obj, name)(*args)


def _set(key, value, obj):
    operator.setitem(obj, key, value)


def _delete(key, obj):
    operator.delitem(obj, key)


def _attribute(name, value, obj):
    setattr(obj, name, value)


def _del_attribute(name, obj):
    delattr(obj, name)


def _actions():
    values = (-99, 0, 1, 10 ** 300, False, True, Attempt.ABOVE, OrdinaryInt(19))
    for key in (0, 1, 2, 3, -1, -2, -4, 4, -5):
        for value in values:
            yield partial(_set, key, value)
        yield partial(_delete, key)
    for key in (slice(None), slice(0, 0), slice(1, 3), slice(None, None, 2), slice(None, None, -1)):
        for values in ([], [91], [7, 8], [9, 8, 7, 6, 5], [True, Attempt.ABOVE, OrdinaryInt(19)]):
            yield partial(_set, key, values)
        yield partial(_delete, key)
    for name, args in (
        ("append", (77,)),
        ("extend", ([77, 88],)),
        ("insert", (0, 77)),
        ("remove", (2,)),
        ("pop", ()),
        ("pop", (0,)),
        ("clear", ()),
        ("reverse", ()),
        ("sort", ()),
    ):
        yield partial(_method, name, args)
    yield lambda obj: obj.sort(reverse=True)
    for values in ([99], [], [False, Attempt.ABOVE, OrdinaryInt(19)]):
        yield lambda obj, values=values: operator.iadd(obj, values)
    for count in (0, -1, 2, False, OrdinaryInt(2)):
        yield lambda obj, count=count: operator.imul(obj, count)
    for name in ("start", "stop", "step"):
        for value in (-3, 0, 1, 6, 17, True, Attempt.ABOVE, OrdinaryInt(19)):
            yield partial(_attribute, name, value)
        yield partial(_del_attribute, name)


def attack(mod: ModuleType) -> bool:
    if not _holds(mod):
        return True
    originals = (mod.BOOTSTRAP, mod.RETRY_DELAYS, mod.schedule(), mod.schedule())
    targets = list(originals)
    for obj in originals:
        for key in (slice(None), slice(1, 3), slice(None, None, -1), slice(None, None, 2), slice(0, 0)):
            targets.append(obj[key])
    actions = tuple(_actions())
    for restore in (True, False):
        for obj in targets:
            for action in actions:
                before = list(obj)
                try:
                    action(obj)
                except Exception:
                    pass
                if not _holds(mod):
                    return True
                if restore:
                    try:
                        obj[:] = before
                    except Exception:
                        pass
                    if not _holds(mod):
                        return True
    return False

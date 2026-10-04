"""D124 반증 - 돌려받은 포트 모음을 여러 변경 수단으로 고친 뒤 is_allowed 와 다음 allowed_ports 를 다시 본다."""

from __future__ import annotations

import enum
from collections.abc import Callable
from types import ModuleType

_LOW, _HIGH = 1024, 49151
_WANT = list(range(_LOW, _HIGH + 1))
# 🔴 is_allowed 를 고정 탐침으로 끝내지 않는다 - 100 칸 걸음 · 경계 양쪽 16칸 · 2의 거듭제곱 ±1 · 잘 알려진 서비스 포트 (독립 검토 · §3.5 표).
#    구간 전체를 다 보면 tuple 로 쥐는 안전한 판에서 in 이 선형이라 26초가 걸린다 [실측] - 임의의 한 칸 구멍은 이 표본이 놓친다.
_WELL_KNOWN = (
    1433, 1521, 2049, 2375, 2376, 3000, 3306, 3389, 4369, 5000, 5432, 5672, 5900, 5984, 6379, 6443, 7001, 8000, 8008, 8080,
    8443, 8888, 9000, 9042, 9090, 9092, 9200, 9300, 9418, 10250, 11211, 15672, 25565, 27017, 27018, 28017, 33060, 37777, 44818,
)
_SWEEP = sorted({
    *range(0, 65536, 100), *range(_LOW - 16, _LOW + 17), *range(_HIGH - 16, _HIGH + 17),
    *(2**k + d for k in range(17) for d in (-1, 0, 1)), *_WELL_KNOWN,
})


class _Port(enum.IntEnum):
    SSH = 22
    LOW = 1024
    HTTP_ALT = 8080
    HIGH = 49151
    EPHEMERAL = 49152


_PROBES: list[int] = [0, 1, 22, 1023, 1024, 1025, 8080, 49150, 49151, 49152, 65535, -1, -1024, 10**30, True, False, *_Port]

# (메서드 이름, 인자) - 시퀀스 · 집합 · 사전 모양의 변경 수단을 모두 친다. 메서드가 없거나 거절되면 안전하다.
_EDITS: list[tuple[str, tuple[object, ...]]] = [
    ("append", (22,)), ("extend", ([22, 23],)), ("insert", (0, 22)), ("remove", (8080,)), ("pop", ()), ("pop", (0,)),
    ("clear", ()), ("sort", ()), ("reverse", ()), ("add", (22,)), ("discard", (8080,)), ("update", ([22],)),
    ("__setitem__", (0, 22)), ("__setitem__", (slice(0, 10), [22])), ("__delitem__", (0,)),
    ("__delitem__", (slice(None),)), ("__iadd__", ([22],)), ("__imul__", (0,)), ("__ior__", ({22},)),
    ("__isub__", ({8080},)), ("__iand__", ({22},)),
]
# 공개 메서드에 넣어 볼 인자 꼴 - 어떤 공개 메서드든 (쓰는 단계 점검)
_ARGS: list[tuple[object, ...]] = [(), (22,), (0,), ([22],), ({22},), (0, 22), (slice(0, 10), [22]), (65535,)]


def _still_right(mod: ModuleType) -> bool:
    try:
        if any(bool(mod.is_allowed(port)) != (_LOW <= port <= _HIGH) for port in _PROBES):
            return False
        return sorted(mod.allowed_ports()) == _WANT
    except Exception:  # noqa: BLE001 - 고친 뒤 묻기만 해도 터지면 바뀐 것이다 (예: release 된 memoryview)
        return False


def _public(obj: object) -> list[str]:
    return [name for name in dir(obj) if not name.startswith("_")]


def _edits_on(obj: object) -> list[Callable[[], object]]:
    """한 객체에 걸 변경 - 위 _EDITS · 공개 메서드를 여러 인자로 · 공개 속성 대입과 삭제.

    🔴 __init__ 다시 부르기는 치지 않는다 - frozen 을 우회하는 의도적 수단이라 주장 밖이다 (object.__setattr__ 과 같다).
    """
    edits: list[Callable[[], object]] = []
    for name, args in _EDITS:
        method = getattr(obj, name, None)
        if callable(method):
            edits.append(lambda method=method, args=args: method(*args))
    for name in _public(obj):
        try:
            attr = getattr(obj, name)
        except Exception:  # noqa: BLE001, S112
            continue
        if callable(attr):
            edits.extend(lambda attr=attr, args=args: attr(*args) for args in _ARGS)
        edits.append(lambda name=name: setattr(obj, name, 22))
        edits.append(lambda name=name: delattr(obj, name))
    return edits


def attack(mod: ModuleType) -> bool:
    """is_allowed 가 경계를 틀리거나, 돌려받은 값을 고친 뒤 is_allowed · 다음 allowed_ports 가 바뀌면 True.

    🔴 변경 수단을 시퀀스에 한정하지 않는다 - set · array · deque 로 쥐는 약화도 그 모양의 메서드로 깨진다.
    🔴 경계 양 끝과 바로 바깥, bool · IntEnum 을 함께 본다 - range 의 끝을 하나 밀거나 당기는 약화가 지나가지 않게.
    🔴 바꿀 수 없어 거절되는 것은 안전하다 - tuple 이나 frozenset 으로 쥐어도 된다. 어떤 예외로 거절되든 묻지 않는다.

    decoy 는 _PORTS 가 range 라 받은 쪽의 어떤 변경도 거절된다.
    twin 은 _PORTS 가 list 라 받은 쪽이 고친 것이 모듈의 허용 목록이 된다.
    """
    if not _still_right(mod):
        return True
    # 돌려받은 값과, 그 값의 공개 속성이 가리키는 값(한 단계 아래 - 예: memoryview.obj)을 고쳐 본다
    for depth in (0, 1):
        got = mod.allowed_ports()
        targets = [got] if depth == 0 else [getattr(got, n, None) for n in _public(got) if not callable(getattr(got, n, None))]
        for target in targets:
            for edit in _edits_on(target):
                try:
                    edit()
                except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
                    pass
                if not _still_right(mod):
                    return True
    # 넓은 표본은 마지막에 한 번 - 변경으로 깨지는 판(list 로 쥔 twin 등)은 위에서 먼저 걸러진다
    return any(bool(mod.is_allowed(port)) != (_LOW <= port <= _HIGH) for port in _SWEEP)

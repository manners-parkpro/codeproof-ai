"""D135 반증 - 호출자의 목록과 행 dict 를 깊은 사본으로 떠 두고, 순위를 매긴 뒤 바뀐 것과 돌려준 목록의 차례 · 순위 · 내용 ·
값 객체를 본다. score 가 없는 행은 dict 하위 타입(defaultdict · Counter)까지 거절하는지 본다."""

from __future__ import annotations

import collections
import copy
import enum
from types import ModuleType


class _Row(dict[str, int]):
    """메서드를 재정의하지 않은 dict 하위 클래스 - 위협 모델 안이다."""


class _Level(enum.IntEnum):
    LOW = 1
    HIGH = 2


def _order(rows: list[dict[str, int]]) -> list[int]:
    """주장 문장대로 - 점수 내림차순 · 같으면 받은 차례. 정렬 키를 베끼지 않고 (-점수, 받은 자리) 로 센다."""
    return sorted(range(len(rows)), key=lambda i: (-rows[i]["score"], i))


def _cases() -> list[list[dict[str, int]]]:
    shared = {"id": 9, "score": 50}
    return [
        [],
        [{"id": 1, "score": 10}],
        [{"id": 1, "score": 10}, {"id": 2, "score": 30}, {"id": 3, "score": 20}],
        [{"id": n, "score": s} for n, s in enumerate([5, 7, 5, 7, 7, 1, 5])],  # 같은 점수가 섞인다 - 받은 차례
        [{"id": 1, "score": 3, "rank": 99}, {"id": 2, "score": 4}],  # 이미 rank 키가 있다
        [{"id": 1, "score": 9, "rank": 1}, {"id": 2, "score": 4}],  # 이미 맞는 rank - 돌려준 행이 호출자의 것이면 안 된다
        [shared, {"id": 2, "score": 60}, shared],  # 같은 dict 가 두 번
        [_Row(id=1, score=2), collections.OrderedDict(id=2, score=8)],  # dict 하위 타입
        [{"id": 1, "score": 0}, {"id": 2, "score": 3}, {"id": 3, "score": -1}],  # 0 · 음수 점수
        # 같은 점수인데 id 와 옛 rank 가 받은 차례와 어긋난다 - id · rank · 행 내용으로 가르는 판이 빠지지 않게
        [{"id": 3, "score": 5, "rank": 1}, {"id": 1, "score": 5, "rank": 3}, {"id": 2, "score": 5, "rank": 2}, {"id": 0, "score": 4}],
        [{"id": 1, "score": _Level.LOW}, {"id": True, "score": _Level.HIGH}],  # IntEnum 점수 · bool 값 - 값 객체를 그대로
        [{"id": 1, "score": 2**53}, {"id": 2, "score": 2**53 + 1}, {"id": 3, "score": -(10**400)}],  # float 로는 같아지거나 넘친다
        # 앞 두 행만 내림차순인 12행 - 정렬을 건너뛰거나 앞 몇 행만 돌려주는 판이 빠지지 않게
        [{"id": n, "score": s} for n, s in enumerate([9, 5, 7, 1, 8, 2, 6, 3, 10, 4, 11, 0])],
    ]


def _refused() -> list[list[dict[str, int]]]:
    return [
        [{"id": 1, "score": 3}, {"id": 2}],
        [{"id": 1}],
        [{"id": 1, "score": 5}, {"id": 2, "points": 9}, {"id": 3, "score": 1}],
        # 🔴 없는 키에 기본값을 내는 dict 하위 타입 - 그 타입 그대로 복사하면 score 가 없는데도 0 이 나온다
        [{"id": 1, "score": 3}, collections.defaultdict(int, id=2)],
        [collections.Counter(id=1)],
        # bool 점수 - int 하위 타입이지만 점수가 아니다 (6라운드 bool 방침 · 덮는 범위 안)
        [{"id": 1, "score": True}, {"id": 2, "score": 2}],
        [{"id": 1, "score": 3}, {"id": 2, "score": False}],
    ]


def attack(mod: ModuleType) -> bool:
    """호출자의 목록이나 행 dict 가 바뀌거나, 돌려준 목록의 차례 · 순위 · 내용이 주장과 다르거나, score 없는 행을 받는가.

    🔴 행 dict 의 내용과 함께 목록이 담은 객체의 정체(id)도 본다 - 목록을 제자리 정렬하는 판은 내용이 아니라 차례가 바뀐다.
    🔴 같은 dict 가 두 번 든 목록 · 이미 맞는 rank 를 가진 행을 준다 - 돌려준 행은 어느 것도 호출자의 dict 가 아니다.
    🔴 돌려준 목록은 빈 목록이어도 새 목록이다. 사본은 원래 값 객체를 그대로 담는다 (bool · IntEnum 이 int 로 바뀌지 않는다).
    🔴 점수는 어떤 int 든 - 2**53 을 넘는 수 · float 로 넘치는 수. 크기 · 받은 차례도 - 앞 두 행만 내림차순인 12행.
    🔴 score 가 없거나 bool 인 행은 거절하되, 거절할 때도 호출자의 것을 바꾸지 않아야 한다. 거절 방식은 묻지 않는다.
    🔴 같은 점수의 id · 옛 rank 는 받은 차례와 어긋나게 둔다 - 그것으로 가르는 판은 둘이 같은 차례면 보이지 않는다.

    decoy 는 행마다 dict 사본을 만든 새 목록을 정렬하고 사본에 rank 를 적는다.
    twin 은 목록만 새로 만들어 호출자의 dict 에 rank 를 적는다.
    """
    for rows in _cases():
        before, ids = copy.deepcopy(rows), [id(row) for row in rows]
        try:
            got = mod.rank(rows)
        except Exception:  # noqa: BLE001 - score 가 모두 있는 목록을 거절하면 깨진 것이다
            return True
        if rows != before or [id(row) for row in rows] != ids or got is rows:
            return True
        order = _order(before)
        if got != [{**before[i], "rank": place} for place, i in enumerate(order, 1)]:
            return True
        if any(any(row is mine for mine in rows) for row in got):
            return True
        if any(any(got[place][key] is not rows[i][key] for key in rows[i] if key != "rank") for place, i in enumerate(order)):
            return True
    for rows in _refused():
        before = copy.deepcopy(rows)
        try:
            mod.rank(rows)
        except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
            if rows != before:
                return True
            continue
        return True
    return False

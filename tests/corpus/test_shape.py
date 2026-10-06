"""가드 위치 분류 - 「증거를 찾으려면 어디를 봐야 하는가」.

🔴 이 축이 왜 필요한가.

`TrapKind` 만으로는 코퍼스가 한쪽으로 쏠렸는지 알 수 없다. 가드가 항상
호출부에 있으면 리뷰어가 「위험한 줄이 비공개 헬퍼면 호출부를 보라」는
**요령만 익혀도** 점수가 나온다 - 추론이 아니라 구조를 학습하는 것이고,
F5 가 per-finding 채점에 대해 말하는 그 문제가 한 층 위에서 반복된다.
"""

from __future__ import annotations

import tomllib
from collections import Counter
from pathlib import Path

import pytest

from codeproof_ai.corpus.decoy import pair_dirs
from codeproof_ai.corpus.shape import GuardShape, classify

DECOYS = Path(__file__).resolve().parents[2] / "corpus" / "decoys"

LOCAL = '''
def total(rows: list[int]) -> int:
    if not rows:
        return 0
    return rows[0] + sum(rows[1:])
'''

CALLER = '''
def _apply(delta: int) -> int:
    return delta * 2


def bump(delta: int) -> int:
    if delta <= 0:
        raise ValueError(delta)
    return _apply(delta)
'''

CALLEE = '''
def sanitize(value: str) -> str:
    if ".." in value:
        raise ValueError(value)
    return value


def open_it(name: str) -> str:
    return sanitize(name)
'''

MODULE = '''
_CMD = "systemctl is-active"


def run() -> str:
    return _CMD
'''

TYPE_INVARIANT = '''
from dataclasses import dataclass


@dataclass(frozen=True)
class Range:
    low: int
    high: int

    def __post_init__(self) -> None:
        if self.high <= self.low:
            raise ValueError((self.low, self.high))


def size(r: Range) -> int:
    return r.high - r.low
'''

TRANSITIVE = '''
def _accumulate(value):
    current = _totals["sum"]
    _totals["sum"] = current + value


def _drain(values):
    for v in values:
        _accumulate(v)


def run(values):
    worker = Thread(target=_drain, args=(values,))
    worker.start()
    worker.join()
'''

NESTED = '''
def outer(x: int) -> int:
    def inner(y: int) -> int:
        return y // x
    if x == 0:
        raise ValueError(x)
    return inner(10)
'''


class TestTheFourShapes:
    @pytest.mark.parametrize(
        ("source", "lure_line", "guard", "expected"),
        [
            (LOCAL, 5, "total", GuardShape.LOCAL),
            (CALLER, 3, "bump", GuardShape.CALLER),
            (CALLEE, 9, "sanitize", GuardShape.CALLEE),
            (MODULE, 6, "_CMD", GuardShape.MODULE),
            (TYPE_INVARIANT, 16, "__post_init__", GuardShape.MODULE),
        ],
        ids=["local", "caller", "callee", "module", "type_invariant"],
    )
    def test_classification(
        self, source: str, lure_line: int, guard: str, expected: GuardShape
    ) -> None:
        assert classify(source, lure_line, guard) is expected

    def test_callee_is_not_caller(self) -> None:
        """🔴 방향이 반대다 - 합치면 「어디를 봐야 하는가」가 사라진다.

        [실측] 이 둘을 구분하지 않는 거친 지표로 세었을 때 "57% 가 한 구조"
        라는 잘못된 결론이 나왔다. 실제로는 32% / 30% 로 갈려 있었다.
        """
        assert classify(CALLER, 3, "bump") is not classify(CALLEE, 9, "sanitize")


class TestCallEdgesAreFollowedProperly:
    """🔴 「어느 방향을 봐야 하는가」는 깊이나 호출 형태와 무관하다."""

    def test_two_hops_still_counts_as_caller(self) -> None:
        """[실측] D051 이 `run` -> `_drain` -> `_accumulate` 로 두 단계였다.

        한 단계만 보던 때는 OTHER 로 떨어졌다.
        """
        assert classify(TRANSITIVE, 3, "run") is GuardShape.CALLER

    def test_a_callback_reference_is_a_call_edge(self) -> None:
        """🔴 `Thread(target=_drain)` 은 호출식이 아니지만 간선이다.

        리뷰어는 그 함수를 따라가야 한다. 호출식만 세면 콜백을 통째로 놓친다 -
        threading · 콜백 등록 · 데코레이터에서 흔한 모양이다.
        """
        body = TRANSITIVE.split("def run")[1]
        # 이 픽스처는 _drain 을 **부르지 않고** 넘기기만 해야 한다
        assert "_drain(" not in body
        assert "target=_drain" in body

        assert classify(TRANSITIVE, 8, "run") is GuardShape.CALLER


class TestItSurvivesRealCode:
    def test_nested_function_is_found(self) -> None:
        """중첩 함수를 놓치지 않는다 - ast.walk 를 쓰면 소실된다 (B3)."""
        assert classify(NESTED, 4, "outer") is GuardShape.CALLER

    def test_broken_source_is_other_not_a_crash(self) -> None:
        assert classify("def (:", 1, "x") is GuardShape.OTHER

    def test_unknown_symbol_is_module_scope(self) -> None:
        assert classify(LOCAL, 5, "nowhere") is GuardShape.MODULE


class TestTheShippedCorpus:
    """🔴 코퍼스가 한 구조로 쏠리지 않았는지."""

    @staticmethod
    def _shapes() -> Counter[str]:
        counts: Counter[str] = Counter()
        for d in pair_dirs(DECOYS):
            meta = tomllib.loads((d / "meta.toml").read_text(encoding="utf-8"))
            counts[
                classify(
                    (d / "decoy.py").read_text(encoding="utf-8"),
                    meta["bait"]["lure_lines"][0],
                    meta["safety"]["guard_symbol"],
                ).value
            ] += 1
        return counts

    def test_every_decoy_is_classified(self) -> None:
        counts = self._shapes()
        assert counts, "코퍼스가 비었다"
        assert counts[GuardShape.OTHER.value] == 0, (
            "OTHER 가 있다 - 분류의 구멍이거나 메타데이터가 어긋난 것이다. "
            "[실측] 처음 2건이 나왔는데 하나는 guard_symbol 관례 불일치(D014), "
            "하나는 타입 불변식이라는 미분류 구조(D018)였다."
        )

    def test_no_single_shape_dominates(self) -> None:
        counts = self._shapes()
        total = sum(counts.values())
        top, n = counts.most_common(1)[0]
        assert n / total <= 0.5, (
            f"'{top}' 가 {n}/{total} ({n / total:.0%}) 다. 한 구조가 절반을 넘으면 "
            "리뷰어가 추론 대신 그 구조를 학습해도 점수가 나온다."
        )

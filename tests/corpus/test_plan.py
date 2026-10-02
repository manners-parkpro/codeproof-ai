"""확장 계획과 코퍼스의 대조 (DESIGN §3.5 「확장 선언」).

🔴 새 쌍이 계획한 빈 칸에 들어갔는지를 사람이 보지 않는다 - 도출한 가드 위치로 센다.
   계획에 없는 칸이나 이미 찬 칸에 들어가면 여기서 멈춘다. 편차라면 `corpus/plan.py` 와
   DESIGN 의 표를 같이 고친다 (둘의 대조는 `tests/docs/test_consistency.py`).
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from codeproof_ai.corpus.decoy import TrapKind
from codeproof_ai.corpus.plan import PLAN
from codeproof_ai.corpus.shape import GuardShape
from codeproof_ai.eval.metrics import TARGET_NEGATIVES
from codeproof_ai.eval.mix import TARGET_PAIRS_PER_KIND

if TYPE_CHECKING:
    from collections.abc import Mapping

    from codeproof_ai.eval.sample import LabeledSample

Cell = tuple[str | None, str | None]


def _target(kind: str | None, shape: str | None) -> int | None:
    """계획한 목표. 계획에 없는 칸(정의상 불가능 · 도출 실패)이면 None."""
    if kind is None or shape is None:
        return None
    try:
        return PLAN[TrapKind(kind)][GuardShape(shape)]
    except (KeyError, ValueError):
        return None


def _misplaced(cells: Mapping[Cell, int]) -> list[str]:
    """계획에 없는 칸이나 목표를 넘긴 칸."""
    out: list[str] = []
    for (kind, shape), n in sorted(cells.items(), key=str):
        target = _target(kind, shape)
        if target is None:
            out.append(f"{kind} x {shape}: {n} - 계획에 없는 칸")
        elif n > target:
            out.append(f"{kind} x {shape}: {n} > 목표 {target}")
    return out


class TestCorpusFollowsThePlan:
    def test_every_pair_sits_in_a_planned_cell(
        self, shipped_samples: list[LabeledSample]
    ) -> None:
        cells: Counter[Cell] = Counter(
            (s.safety.category, s.safety.shape) for s in shipped_samples if s.safety is not None
        )
        assert sum(cells.values()) > 0, "대조군 - 센 음성이 있어야 이 테스트가 뭔가를 본다"
        misplaced = _misplaced(cells)
        assert not misplaced, (
            "계획한 빈 칸이 아닌 곳에 쌍이 있다 (DESIGN §3.5). 편차면 corpus/plan.py 와 "
            "DESIGN 의 표를 같이 고친다 - 물림을 보고 옮기지 않는다:\n" + "\n".join(misplaced)
        )

    def test_it_catches_a_pair_outside_the_plan(self) -> None:
        """대조군 - 위 테스트의 「0건」이 판정 능력에서 나오는지 본다."""
        assert _misplaced({("caller_held_lock", "local"): 1}) == [
            "caller_held_lock x local: 1 - 계획에 없는 칸"
        ]
        assert _misplaced({("caller_held_lock", "caller"): 11}) == [
            "caller_held_lock x caller: 11 > 목표 10"
        ]
        assert _misplaced({("caller_held_lock", None): 1}) == [
            "caller_held_lock x None: 1 - 계획에 없는 칸"
        ]
        assert _misplaced({("caller_held_lock", "caller"): 10}) == []


def test_plan_meets_the_declared_targets() -> None:
    """합은 발표용 표본 크기, 분류마다 선언한 최소 쌍 수 이상 - 둘 다 이미 코드에 있는 선언이다."""
    assert set(PLAN) == set(TrapKind), "계획에 없는 분류가 있다"
    assert sum(n for cells in PLAN.values() for n in cells.values()) == TARGET_NEGATIVES
    short = {
        k.value: sum(cells.values())
        for k, cells in PLAN.items()
        if sum(cells.values()) < TARGET_PAIRS_PER_KIND
    }
    assert not short, f"분류당 최소 {TARGET_PAIRS_PER_KIND}쌍에 못 미친다: {short}"

"""한눈에 (eval/glance.py) - 예시 짝을 고르는 규칙.

🔴 예시는 손으로 고르지 않는다 - 규칙이 고른다. 규칙이 slack 0 의 판정만 보면 결함 옆 줄에 낸
   맞는 지적이 「놓침」인 짝이 뽑힌다 [실측 · 150쌍 · D140 - Codex 가 3회 모두 XSS 를 짚었는데
   slack 0 에서 P-B].
"""

from __future__ import annotations

from codeproof_ai.eval.glance import fixed, near_miss, pick_examples
from codeproof_ai.eval.pairing import PairVerdict

C, V, U, R = (
    PairVerdict.CORRECT,
    PairVerdict.OVER_FLAG,
    PairVerdict.UNDER_FLAG,
    PairVerdict.REVERSED,
)
SLACKS = (0, 2, 5, 10)
RUNS = 3

Side = PairVerdict | list[PairVerdict] | dict[int, PairVerdict | list[PairVerdict]]


def _verdict(side: Side, slack: int, run: int) -> PairVerdict:
    """판정 하나면 늘 같고, 목록이면 회차마다, 사전이면 slack 마다 (그 안에서 회차마다) 다르다."""
    if isinstance(side, dict):
        at = side[slack]
        return at[run] if isinstance(at, list) else at
    if isinstance(side, list):
        return side[run]
    return side


def _ladder(
    spec: dict[str, tuple[Side, Side]],
) -> dict[int, tuple[list[dict[str, PairVerdict]], list[dict[str, PairVerdict]]]]:
    return {
        s: (
            [{p: _verdict(v[0], s, r) for p, v in spec.items()} for r in range(RUNS)],
            [{p: _verdict(v[1], s, r) for p, v in spec.items()} for r in range(RUNS)],
        )
        for s in SLACKS
    }


class TestFixed:
    def test_a_verdict_held_everywhere(self) -> None:
        assert fixed(_ladder({"D1": (C, U)}), 0, "D1") is C

    def test_a_verdict_that_moves_is_not_fixed(self) -> None:
        ladder = _ladder({"D1": (C, {0: U, 2: C, 5: C, 10: C})})
        assert fixed(ladder, 1, "D1") is None


class TestPickExamples:
    def test_each_direction_gets_its_shortest_pair(self) -> None:
        ladder = _ladder({"D1": (C, U), "D2": (C, U), "D3": (V, C)})
        picked = pick_examples(ladder, {"D1": 12, "D2": 9, "D3": 20})
        assert picked == [("D2", 0, U), ("D3", 1, V)]

    def test_a_verdict_that_moves_with_slack_is_not_an_example(self) -> None:
        """🔴 D140 - slack 0 에서만 「놓침」인 짝은 매칭 정책의 산물이다.

        더 길어도 늘 놓친 짝을 고른다.
        """
        ladder = _ladder({"D140": (C, {0: U, 2: C, 5: C, 10: C}), "D200": (C, U)})
        assert pick_examples(ladder, {"D140": 9, "D200": 30}) == [("D200", 0, U)]

    def test_a_verdict_that_moves_between_runs_is_not_an_example(self) -> None:
        ladder = _ladder({"D5": (C, [U, U, C]), "D6": ([C, C, U], U)})
        assert pick_examples(ladder, {"D5": 5, "D6": 6}) == []

    def test_ties_go_to_the_identifier(self) -> None:
        ladder = _ladder({"D9": (C, U), "D8": (C, R)})
        assert pick_examples(ladder, {"D9": 10, "D8": 10}) == [("D8", 0, R)]

    def test_both_correct_is_not_a_split(self) -> None:
        assert pick_examples(_ladder({"D1": (C, C)}), {"D1": 3}) == []


class TestNearMiss:
    """결함 근처를 가리켰는데 slack 0 에서는 「놓침」인 짝 - 첫 화면 카드의 예시다."""

    def test_missed_strictly_but_caught_one_step_wider(self) -> None:
        ladder = _ladder({"D140": (C, {0: U, 2: C, 5: C, 10: C}), "D9": (C, U)})
        assert near_miss(ladder, {"D140": 9, "D9": 5}, 1) == "D140"  # 늘 놓친 D9 는 아니다

    def test_every_run_must_move(self) -> None:
        """🔴 한 회차만 옮겨 가는 짝은 실행 변동과 매칭 정책이 섞인다."""
        ladder = _ladder({"D1": (C, {0: U, 2: [C, C, U], 5: C, 10: C})})
        assert near_miss(ladder, {"D1": 4}, 1) is None

    def test_the_shortest_pair_wins(self) -> None:
        moving: Side = {0: R, 2: V, 5: V, 10: V}
        ladder = _ladder({"D2": (moving, C), "D3": (moving, C)})
        assert near_miss(ladder, {"D2": 30, "D3": 12}, 0) == "D3"

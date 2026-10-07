"""생성 그림 (eval/figures.py) - 받은 값만 그리고, 같은 값이면 같은 바이트다.

🔴 그림은 README 첫 화면에 실린다 - 숫자가 빠지거나 바깥 자원을 부르면 GitHub 에서 조용히 깨진다.
"""

from __future__ import annotations

import dataclasses
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.eval.figures import (
    BANNER,
    CODE_LINES,
    Estimate,
    Example,
    ExampleSide,
    PairCounts,
    PairRung,
    Scoreboard,
    ScoreRow,
    Share,
    Spread,
    _clip,
    _units,
    agents_svg,
    examples_svg,
    pairs_svg,
    scoreboard_svg,
    spread_svg,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SVG = "{http://www.w3.org/2000/svg}"
SPREADS = [Spread("F,E", 34, 0, 34), Spread("S", 8, 8, 8), Spread("ALL", 777, 17, 777)]
RUNGS = [
    PairRung("ALL", "provable_safety", 0, PairCounts("provable_safety", 1, 5, 134, 10)),
    PairRung("ALL", "injected_defect", 0, PairCounts("injected_defect", 0, 26, 0, 124)),
    PairRung("ALL", "provable_safety", 10, PairCounts("provable_safety", 7, 14, 127, 2)),
    PairRung("ALL", "injected_defect", 10, PairCounts("injected_defect", 0, 150, 0, 0)),
    PairRung("S", "provable_safety", 0, PairCounts("provable_safety", 2, 3, 140, 5)),
    PairRung("S", "injected_defect", 0, PairCounts("injected_defect", 2, 3, 140, 5)),
]
RATES = [("claude-code-neutral", 0.647), ("codex-cli-neutral", 0.469)]
LADDER = [(0, Estimate("slack 0", 0.178, 0.111, 0.249)),
          (10, Estimate("slack 10", 0.120, 0.049, 0.191))]
BOARD = Scoreboard(
    names=("Claude Code", "Codex CLI"),
    models=("claude-fable-5-1", "gpt-6-astra"),
    pairs=150,
    runs=(3, 3),
    slacks=(0, 2, 5, 10),
    rows=(
        ScoreRow("버그를 짚었다", "가드를 지운 판의 결함 자리를 짚었다", ("P-C", "P-V"),
                 Share(0.696, 0.884), Share(0.476, 0.700),
                 Estimate("slack 0", 0.220, 0.156, 0.287), stable=True),
        ScoreRow("안전한 코드에 헛경고", "증명된 안전한 판에 결함을 주장했다", ("P-V", "P-R"),
                 Share(0.071, 0.100), Share(0.020, 0.036),
                 Estimate("slack 0", 0.051, -0.011, 0.093), stable=False),
        ScoreRow("버그만 정확히 짚었다", "안전한 코드는 통과, 버그만 지적", ("P-C",),
                 Share(0.647, 0.784), Share(0.469, 0.664),
                 Estimate("slack 0", 0.178, 0.111, 0.249), stable=True, primary=True),
    ),
    conditions="effort low · 같은 프롬프트 · docstring neutral",
)
EXAMPLES = (
    Example(
        "D117-page-size", "bounded_input", 10, ("limit = min(limit, _MAX_PAGE)",), (),
        "limit 을 상한으로 줄이는 줄이 없다.",
        ExampleSide("Claude Code", "P-C", 3),
        ExampleSide("Codex CLI", "P-B", 3, silent=True),
    ),
    Example(
        "D069-retry", "idempotent_retry", 20, ("_ledger[delivery_id] = row",),
        ('_ledger[f"row-{len(_ledger)}"] = row',), "적립 행의 키를 매번 새로 만든다.",
        ExampleSide("Codex CLI", "P-C", 3),
        ExampleSide("Claude Code", "P-V", 3),
    ),
)
FIGURES: dict[str, Callable[[], str]] = {
    "spread": lambda: spread_svg(SPREADS, 150),
    "pairs": lambda: pairs_svg(RUNGS),
    "agents": lambda: agents_svg(RATES, LADDER, pairs=150, runs=(3, 3)),
    "scoreboard": lambda: scoreboard_svg(BOARD),
    "examples": lambda: examples_svg(EXAMPLES, pairs=150, kinds=14),
}


def _texts(svg: str) -> list[str]:
    return [t.text or "" for t in ET.fromstring(svg).iter(f"{SVG}text")]


class TestEveryFigure:
    @pytest.mark.parametrize("name", sorted(FIGURES))
    def test_it_says_it_is_generated(self, name: str) -> None:
        assert FIGURES[name]().startswith(BANNER)

    @pytest.mark.parametrize("name", sorted(FIGURES))
    def test_it_is_well_formed_and_deterministic(self, name: str) -> None:
        svg = FIGURES[name]()
        assert ET.fromstring(svg).tag == f"{SVG}svg"
        assert svg == FIGURES[name]()

    @pytest.mark.parametrize("name", sorted(FIGURES))
    def test_it_loads_nothing_from_outside(self, name: str) -> None:
        """GitHub 은 그림 안의 스크립트 · 바깥 자원을 막는다 - 넣으면 그 부분만 조용히 빠진다."""
        svg = FIGURES[name]().replace('xmlns="http://www.w3.org/2000/svg"', "")
        assert "http" not in svg
        assert "<script" not in svg
        assert "href" not in svg


class TestSpread:
    def test_every_selection_shows_both_numbers_and_the_verdict(self) -> None:
        texts = _texts(spread_svg(SPREADS, 150))
        for want in ("0 대 34", "8 대 8", "17 대 777", "45.7배", "일치", "배수로 잴 수 없다"):
            assert want in texts
        assert "전체 규칙 (ALL)" in texts
        assert any("위치는 정확히 겹친 것만 인정" in t for t in texts)  # 매칭 조건을 그림이 말한다

    @pytest.mark.parametrize(
        ("spread", "want"),
        [
            (Spread("ALL", 777, 17, 777), "45.7배"),
            (Spread("S", 8, 8, 8), "일치"),
            (Spread("F,E", 34, 0, 34), "배수로 잴 수 없다"),
        ],
    )
    def test_the_verdict_never_divides_by_zero(self, spread: Spread, want: str) -> None:
        assert spread.verdict == want

    def test_a_zero_bar_is_not_drawn_but_its_number_is(self) -> None:
        svg = spread_svg([Spread("F,E", 34, 0, 34)], 150)
        bars = [r for r in ET.fromstring(svg).iter(f"{SVG}rect") if r.get("class") == "safe"]
        assert len(bars) == 1  # 범례의 견본 하나뿐 - FP 0 의 막대는 없다
        assert "0" in _texts(svg)


class TestPairs:
    def test_each_definition_gets_its_own_bar_and_wide_segments_are_labelled(self) -> None:
        texts = _texts(pairs_svg(RUNGS))
        assert texts.count("provable_safety") == 2
        for want in ("134", "124", "26", "140"):
            assert want in texts
        assert "127" not in texts  # 막대는 slack 0 이다 - 다른 칸의 수는 막대에 없다

    def test_the_ladder_column_says_whether_the_verdict_moves(self) -> None:
        """🔴 막대(slack 0)만으로는 「역전」이 정의의 것인지 매칭 정책의 것인지 모른다 (A2a)."""
        texts = _texts(pairs_svg(RUNGS))
        assert "P-R·P-V 흔들린다" in texts
        assert "P-B·P-B 안정" in texts
        assert "slack 0·10" in texts
        assert any("막대는 slack 0" in t and "150쌍" in t for t in texts)

    def test_a_definition_with_no_pairs_draws_nothing(self) -> None:
        empty = PairCounts("provable_safety", 0, 0, 0, 0)
        svg = pairs_svg([PairRung("ALL", "provable_safety", 0, empty)])
        assert not [r for r in ET.fromstring(svg).iter(f"{SVG}rect") if r.get("class") == "pb"][1:]
        assert "-" in _texts(svg)  # 짝이 없으면 판정도 「안정」도 없다

    @pytest.mark.parametrize(
        ("counts", "want"),
        [
            (PairCounts("g", 0, 26, 0, 124), "P-R"),
            (PairCounts("g", 0, 109, 0, 41), "P-V"),
            (PairCounts("g", 1, 1, 0, 0), "P-C"),  # 같으면 앞선 것
            (PairCounts("g", 0, 0, 0, 0), "-"),
        ],
    )
    def test_the_dominant_verdict(self, counts: PairCounts, want: str) -> None:
        assert counts.dominant == want


class TestAgents:
    def test_rates_are_points_and_only_the_difference_carries_an_interval(self) -> None:
        """🔴 리뷰어마다의 구간을 겹쳐 그리면 F6 이 금지한 읽기를 그림이 권한다."""
        svg = agents_svg(RATES, LADDER, pairs=150, runs=(3, 3))
        texts = _texts(svg)
        assert "64.7%" in texts
        assert "46.9%" in texts
        lines = ET.fromstring(svg).iter(f"{SVG}line")
        whiskers = [ln for ln in lines if ln.get("class") == "whisker"]
        assert len(whiskers) == len(LADDER)
        assert "+17.8%p [+11.1, +24.9]" in texts
        assert "+12.0%p [+4.9, +19.1]" in texts
        assert any("claude-code-neutral - codex-cli-neutral" in t for t in texts)

    def test_the_subtitle_states_the_measurement_conditions(self) -> None:
        texts = _texts(agents_svg(RATES, LADDER, pairs=150, runs=(3, 3)))
        assert any("slack 0" in t and "150쌍" in t and "샘플당 3회" in t for t in texts)
        assert any("구별 성공(P-C)" in t for t in texts)  # 무엇의 비율인지 그림만 봐도 안다


class TestScoreboard:
    def test_values_are_the_declared_matching(self) -> None:
        texts = _texts(scoreboard_svg(BOARD))
        for want in ("69.6%", "47.6%", "7.1%", "2.0%", "64.7%", "46.9%"):
            assert want in texts
        assert not [t for t in texts if "88.4" in t]  # 사다리 끝 값은 그림에 없다 - 생성물에 있다

    def test_only_the_primary_difference_carries_an_interval(self) -> None:
        """🔴 리뷰어마다의 구간을 싣지 않는다 - 두 구간을 겹쳐 보는 읽기를 권하게 된다 (F6)."""
        svg = scoreboard_svg(BOARD)
        assert [t for t in _texts(svg) if "[" in t] == ["95% 신뢰구간 [+11.1, +24.9]"]
        assert "차이 +17.8%p" in _texts(svg)
        lines = ET.fromstring(svg).iter(f"{SVG}line")
        assert not [ln for ln in lines if ln.get("class") == "whisker"]

    def test_an_interval_that_holds_zero_is_not_distinguishable(self) -> None:
        wide = dataclasses.replace(BOARD.rows[2], diff=Estimate("slack 0", 0.02, -0.01, 0.05))
        texts = _texts(scoreboard_svg(dataclasses.replace(BOARD, rows=(*BOARD.rows[:2], wide))))
        assert "95% 신뢰구간 [-1.0, +5.0]" in texts
        assert "우연일 수 있다" in texts
        assert "우연으로 보기 어렵다" in _texts(scoreboard_svg(BOARD))

    def test_the_ladder_is_one_line(self) -> None:
        """사다리 값은 생성물에 두고 그림에는 판정이 같은지만 적는다 (A2a)."""
        texts = _texts(scoreboard_svg(BOARD))
        assert any("결론이 바뀐다: 안전한 코드에 헛경고" in t for t in texts)
        steady = dataclasses.replace(
            BOARD, rows=tuple(dataclasses.replace(r, stable=True) for r in BOARD.rows)
        )
        steady_texts = _texts(scoreboard_svg(steady))
        assert any("10줄)까지 지적을 인정해도 결론은 같다" in t for t in steady_texts)

    def test_it_names_the_primary_metric_the_grader_and_the_models(self) -> None:
        texts = _texts(scoreboard_svg(BOARD))
        assert "버그만 정확히 짚었다 (핵심)" in texts
        assert any("provable_safety" in t and "짝마다 3회" in t for t in texts)  # F5 - 어느 정의
        assert "Claude Code · claude-fable-5-1" in texts
        assert any("effort low" in t for t in texts)

    def test_no_line_runs_past_the_frame(self) -> None:
        """SVG 글은 줄을 바꾸지 않는다 - 긴 주석은 잘라서 싣는다."""
        assert max(_units(t) for t in _texts(scoreboard_svg(BOARD))) <= 130


class TestExamples:
    def test_each_pair_shows_the_change_and_both_verdicts(self) -> None:
        texts = _texts(examples_svg(EXAMPLES, pairs=150, kinds=14))
        for want in (
            "버그 — limit 을 상한으로 줄이는 줄이 없다.",
            "D117 · 코드 10줄",
            "- limit = min(limit, _MAX_PAGE)",
            "+ (지운 줄)",
            "✓ Claude Code · 3회 모두 버그만 지적",
            "✗ Codex CLI · 3회 모두 아무 지적 없음",
            "✗ Claude Code · 3회 모두 안전한 코드에도 경고",
        ):
            assert want in texts
        assert any("규칙으로 골랐다" in t for t in texts)  # 손으로 고르지 않았다고 그림이 말한다

    def test_many_changed_lines_are_cut(self) -> None:
        many = tuple(f"x{i} = {i}" for i in range(CODE_LINES + 2))
        ex = Example("D1", "k", 30, many, ("y = 0",), "결함.",
                     ExampleSide("A", "P-C", 3), ExampleSide("B", "P-B", 3))
        texts = _texts(examples_svg([ex], pairs=1, kinds=1))
        assert [t for t in texts if t.startswith("- ")] == [
            *(f"- x{i} = {i}" for i in range(CODE_LINES - 1)), "- …"
        ]


class TestTextFitting:
    @pytest.mark.parametrize(
        ("text", "units", "want"),
        [("abcdef", 6, "abcdef"), ("abcdefg", 6, "abcde…"), ("가나다라", 5, "가나…")],
    )
    def test_clip_counts_wide_characters_twice(self, text: str, units: int, want: str) -> None:
        assert _clip(text, units) == want

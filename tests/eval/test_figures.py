"""생성 그림 (eval/figures.py) - 받은 값만 그리고, 같은 값이면 같은 바이트다.

🔴 그림은 README 첫 화면에 실린다 - 숫자가 빠지거나 바깥 자원을 부르면 GitHub 에서 조용히 깨진다.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import pytest

from codeproof_ai.eval.figures import (
    BANNER,
    Estimate,
    PairCounts,
    PairRung,
    Spread,
    agents_svg,
    pairs_svg,
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
FIGURES: dict[str, Callable[[], str]] = {
    "spread": lambda: spread_svg(SPREADS, 150),
    "pairs": lambda: pairs_svg(RUNGS),
    "agents": lambda: agents_svg(RATES, LADDER, pairs=150, runs=(3, 3)),
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
        assert "--ruff-select ALL" in texts
        assert any("slack 0" in t for t in texts)  # 어느 매칭 조건의 숫자인지 그림만 봐도 안다

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

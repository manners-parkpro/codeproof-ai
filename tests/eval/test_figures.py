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
    Spread,
    agents_svg,
    pairs_svg,
    spread_svg,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SVG = "{http://www.w3.org/2000/svg}"
SPREADS = [Spread("F,E", 34, 0, 34), Spread("S", 8, 8, 8), Spread("ALL", 777, 17, 777)]
PAIRS = [
    ("ALL", [PairCounts("provable_safety", 1, 5, 134, 10),
             PairCounts("injected_defect", 0, 26, 0, 124)]),
    ("S", [PairCounts("provable_safety", 2, 3, 140, 5),
           PairCounts("injected_defect", 2, 3, 140, 5)]),
]
RATES = [Estimate("claude-code-neutral", 0.647, 0.576, 0.720),
         Estimate("codex-cli-neutral", 0.469, 0.389, 0.547)]
LADDER = [(0, Estimate("slack 0", 0.178, 0.111, 0.249)),
          (10, Estimate("slack 10", 0.120, 0.049, 0.191))]
FIGURES: dict[str, Callable[[], str]] = {
    "spread": lambda: spread_svg(SPREADS, 150),
    "pairs": lambda: pairs_svg(PAIRS),
    "agents": lambda: agents_svg(RATES, LADDER),
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
        texts = _texts(pairs_svg(PAIRS))
        assert texts.count("provable_safety") == 2
        for want in ("134", "124", "26", "140"):
            assert want in texts

    def test_a_definition_with_no_pairs_draws_nothing(self) -> None:
        svg = pairs_svg([("ALL", [PairCounts("provable_safety", 0, 0, 0, 0)])])
        assert not [r for r in ET.fromstring(svg).iter(f"{SVG}rect") if r.get("class") == "pb"][1:]


class TestAgents:
    def test_rates_and_every_rung_of_the_ladder_carry_their_interval(self) -> None:
        texts = _texts(agents_svg(RATES, LADDER))
        assert "64.7% [57.6, 72.0]" in texts
        assert "46.9% [38.9, 54.7]" in texts
        assert "+17.8%p [+11.1, +24.9]" in texts
        assert "+12.0%p [+4.9, +19.1]" in texts
        assert any("claude-code-neutral - codex-cli-neutral" in t for t in texts)

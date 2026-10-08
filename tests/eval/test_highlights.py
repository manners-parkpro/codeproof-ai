"""랜딩 페이지 첫 화면의 생성 구간 - 답 · 주 지표 카드 · 핵심 발견 카드 (F5b).

🔴 방향 말(「앞섰다」 · 「차이가 남았다」 · 「대신」)도 값에서 고른다. 손으로 쓰면 다시 잰 뒤
   방향이 바뀌어도 문장이 남는다 - 값을 뒤집어 문장이 따라오는지 본다.
"""

from __future__ import annotations

import dataclasses

from codeproof_ai.eval.figures import Estimate, Scoreboard, ScoreRow, Share, Spread
from codeproof_ai.eval.report import Glance, render_highlights

CAUGHT = ScoreRow("버그를 짚었다", "버그 코드의 결함을 지적", ("P-C", "P-V"),
                  Share(0.696, 0.884), Share(0.476, 0.700),
                  Estimate("slack 0", 0.22, 0.156, 0.287), stable=True)
ALARM = ScoreRow("안전한 코드에 헛경고", "안전한 코드에 결함이 있다고 함", ("P-V", "P-R"),
                 Share(0.071, 0.100), Share(0.020, 0.036),
                 Estimate("slack 0", 0.051, 0.011, 0.093), stable=True)
PRIMARY = ScoreRow("버그만 정확히 짚었다", "안전한 코드는 통과, 버그만 지적", ("P-C",),
                   Share(0.647, 0.784), Share(0.469, 0.664),
                   Estimate("slack 0", 0.178, 0.111, 0.249), stable=True, primary=True)
ALL = Spread("ALL", 900, 17, 777)
SECURITY = Spread("S", 40, 8, 8)


def _glance(*rows: ScoreRow) -> Glance:
    board = Scoreboard(("Claude Code", "Codex CLI"), ("m-a", "m-b"), pairs=150, runs=(3, 3),
                       slacks=(0, 2, 5, 10), rows=rows)
    return Glance(("a", "b"), board, examples=(), near=None, kinds=14)


def _answer(page: str) -> str:
    return page.split('<p class="answer">', 1)[1].split("</p>", 1)[0]


def _flip(row: ScoreRow) -> ScoreRow:
    """두 리뷰어를 맞바꾼 값 - 방향 말이 따라 바뀌어야 한다."""
    d = row.diff
    flipped = Estimate(d.label, -d.point, -d.hi, -d.lo)
    return dataclasses.replace(row, a=row.b, b=row.a, diff=flipped)


class TestTheAnswerFollowsTheValues:
    def test_a_stable_lead(self) -> None:
        page = render_highlights([ALL, SECURITY], _glance(CAUGHT, ALARM, PRIMARY))
        answer = _answer(page)
        assert "Claude Code 가 앞섰고" in answer
        assert "근처 10줄까지 넓혀 세도 차이가 남았다 (78.4% 대 66.4%)" in answer
        assert "45.7배 갈렸다" in answer
        assert "0 을 포함하지 않는다" in page

    def test_the_other_reviewer_leads(self) -> None:
        answer = _answer(render_highlights([ALL], _glance(CAUGHT, ALARM, _flip(PRIMARY))))
        assert "Codex CLI 가 앞섰고" in answer

    def test_an_interval_around_zero(self) -> None:
        flat = dataclasses.replace(PRIMARY, diff=Estimate("slack 0", 0.03, -0.04, 0.10))
        page = render_highlights([ALL], _glance(CAUGHT, ALARM, flat))
        assert "구별되지 않았다" in _answer(page)
        assert "앞섰" not in _answer(page)
        assert "0 을 포함한다" in page

    def test_a_shaky_ladder_claims_no_rank(self) -> None:
        shaky = dataclasses.replace(PRIMARY, stable=False)
        answer = _answer(render_highlights([ALL], _glance(CAUGHT, ALARM, shaky)))
        assert "순위를 주장하지 않는다" in answer
        assert "차이가 남았다" not in answer


class TestTheCards:
    def test_security_rules_alone_agree(self) -> None:
        page = render_highlights([ALL, SECURITY], _glance(CAUGHT, ALARM, PRIMARY))
        assert '<p class="big">45.7배</p>' in page
        assert "보안 규칙만 고르면 8 대 8로 같다." in page

    def test_the_trade_off_word_comes_from_the_values(self) -> None:
        """「대신」은 많이 짚는 쪽이 헛경고도 더 낼 때만이다."""
        same = render_highlights([ALL], _glance(CAUGHT, ALARM, PRIMARY))
        other = render_highlights([ALL], _glance(CAUGHT, _flip(ALARM), PRIMARY))
        assert "대신 헛경고는" in same
        assert "대신 헛경고는" not in other
        assert "Codex CLI 가 더 높았다." in other

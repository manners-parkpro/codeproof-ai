"""인용 검증 - 모델이 인용한 코드가 실제로 거기 있는가.

구현 비용이 거의 0 인데 강력하다. 인용이 존재하지 않으면 그 지적은
**존재하지 않는 코드**에 대한 것이고, 다른 어떤 근거도 의미가 없다.

⚠ 선행연구 확인: 환각 탐지 자체는 이미 발표돼 있다
  (HalluJudge 2026-01, 환각률 22%, κ 0.78-0.84).
  여기서는 독립 기여로 주장하지 않고, **confidence 의 하드 게이트**로만 쓴다.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING

from codeproof_ai.domain.evidence import Evidence, EvidenceKind, Verdict

if TYPE_CHECKING:
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()


class MatchLevel(StrEnum):
    """어느 수준에서 일치했는가. 🔴 이진 판정보다 정보가 많다."""

    EXACT_AT_LINE = "exact_at_line"
    """주장한 줄에 원문 그대로 있다."""

    NORMALIZED_AT_LINE = "normalized_at_line"
    """주장한 줄에 있으나 공백이 다르다 - 재포맷일 뿐 환각이 아니다."""

    ELSEWHERE_IN_FILE = "elsewhere_in_file"
    """파일 안에 있으나 다른 줄이다 - 위치가 틀렸지 코드는 실재한다."""

    NOT_FOUND = "not_found"
    """🔴 파일 어디에도 없다. 존재하지 않는 코드에 대한 지적이다."""


class CitationVerifier:
    """인용문이 제시된 파일에 실재하는지 본다."""

    kind = EvidenceKind.CITATION.value

    def __init__(self, line_window: int = 2, *, normalize: bool = True) -> None:
        """Args:
        line_window: 주장한 줄에서 몇 줄까지 "그 자리" 로 볼지.
            🔴 손잡이다 - 넓히면 위치 오류가 정답으로 넘어온다.
        normalize: 공백 차이를 무시할지. 끄면 재포맷이 환각으로 잡힌다.
        """
        if line_window < 0:
            msg = f"line_window 는 0 이상이다: {line_window}"
            raise ValueError(msg)
        self.line_window = line_window
        self.normalize = normalize

    def config_signature(self) -> str:
        return f"citation(window={self.line_window},norm={self.normalize})"

    def match_level(self, finding: Finding, target: ReviewTarget) -> MatchLevel | None:
        """일치 수준. 인용문이 없으면 None."""
        quote = (finding.quoted_code or "").strip()
        if not quote:
            return None
        src = target.file(finding.location.path)
        if src is None:
            return MatchLevel.NOT_FOUND

        lines = src.content.splitlines()
        span = finding.location.span
        claimed = span.start.line
        last = max(claimed, span.end.line if span.end is not None else claimed)
        # 🔴 여러 줄 인용은 그 줄 수만큼 창을 넓혀 이어 붙인 본문과 대조한다 - 한 줄씩 보면
        #    정확히 그 자리에 있는 인용도 「위치 오류」가 된다 [실측: 측정 묶음의 에이전트
        #    지적 claude 339/479 · codex 172/341 이 그 경우였다].
        height = quote.count("\n") + 1
        lo = max(1, claimed - self.line_window)
        hi = min(len(lines), max(last, claimed + height - 1) + self.line_window)

        return self._locate(quote, lines[lo - 1 : hi], src.content)

    def _locate(
        self, quote: str, window: list[str], whole: str
    ) -> MatchLevel:
        multi = "\n" in quote
        if (quote in "\n".join(window)) if multi else any(quote in ln for ln in window):
            return MatchLevel.EXACT_AT_LINE
        if not self.normalize:
            return (
                MatchLevel.ELSEWHERE_IN_FILE
                if quote in whole
                else MatchLevel.NOT_FOUND
            )
        nq = _norm(quote)
        if not nq:
            return MatchLevel.NOT_FOUND
        if (nq in _norm(" ".join(window))) if multi else any(nq in _norm(ln) for ln in window):
            return MatchLevel.NORMALIZED_AT_LINE
        return (
            MatchLevel.ELSEWHERE_IN_FILE
            if nq in _norm(whole)
            else MatchLevel.NOT_FOUND
        )

    def verify(self, finding: Finding, target: ReviewTarget) -> Evidence:
        level = self.match_level(finding, target)
        if level is None:
            return Evidence(
                kind=EvidenceKind.CITATION,
                verdict=Verdict.NOT_APPLICABLE,
                detail="인용문이 없다 - 검증할 대상이 없다",
            )

        if level in {MatchLevel.EXACT_AT_LINE, MatchLevel.NORMALIZED_AT_LINE}:
            verdict, detail = Verdict.SUPPORTS, f"인용문이 주장한 위치에 있다 ({level})"
        elif level is MatchLevel.ELSEWHERE_IN_FILE:
            # 🔴 위치가 틀린 것과 코드가 없는 것은 다르다.
            verdict, detail = (
                Verdict.INCONCLUSIVE,
                "인용문이 파일에는 있으나 주장한 줄이 아니다 - 위치 오류지 환각이 아니다",
            )
        else:
            verdict, detail = (
                Verdict.REFUTES,
                "인용문이 제시된 코드 어디에도 없다 - 존재하지 않는 코드에 대한 지적이다",
            )

        return Evidence(
            kind=EvidenceKind.CITATION,
            verdict=verdict,
            detail=detail,
            locator=f"{finding.location.path}:{finding.location.line}",
        )

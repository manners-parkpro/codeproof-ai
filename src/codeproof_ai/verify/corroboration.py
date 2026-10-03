"""교차 확인 - 독립 도구가 같은 자리를 지적했는가.

🔴 이 검증자는 **도구를 돌리지 않는다.** 이미 계산된 지적을 생성자로 받는다.
   verify/ 가 analysis/ 를 import 하면 레이어가 깨지고, 검증 단위 테스트에
   subprocess 가 끌려 들어온다.

🔴 그리고 동의가 없는 것은 **반증이 아니다.** 확인자가 그 층을 아예 안 볼 수도 있다
   (실측: Ruff 는 S602 를 보지만 mypy 에는 보안 규칙이 없다).
   그래서 REFUTES 를 내지 않는다 - SUPPORTS 아니면 INCONCLUSIVE 다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.domain.evidence import Evidence, EvidenceKind, Verdict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget


class SelfCorroborationError(ValueError):
    """평가 대상이 자기 자신을 확인하려 했다.

    같은 도구의 지적을 같은 도구로 확인하면 항상 일치한다 -
    측정이 아니라 항등식이다.
    """


class CorroborationVerifier:
    """독립 도구의 지적과 위치가 겹치는지 본다."""

    kind = EvidenceKind.CORROBORATION.value

    def __init__(
        self, reference: Sequence[Finding], line_slack: int = 2
    ) -> None:
        """Args:
        reference: 확인자의 지적. **엔진이 미리 계산해 넘긴다.**
        line_slack: 몇 줄까지 "같은 자리" 로 볼지. 🔴 손잡이다.
        """
        if line_slack < 0:
            msg = f"line_slack 은 0 이상이다: {line_slack}"
            raise ValueError(msg)
        self.line_slack = line_slack
        self._sources = frozenset(f.source for f in reference)
        self._hits = frozenset(
            (f.location.path, f.location.line) for f in reference
        )

    def config_signature(self) -> str:
        who = "+".join(sorted(self._sources)) or "none"
        return f"corroboration(ref={who},slack={self.line_slack},match=span)"

    def verify(self, finding: Finding, target: ReviewTarget) -> Evidence:  # noqa: ARG002
        if finding.source in self._sources:
            msg = (
                f"확인자에 평가 대상({finding.source})의 지적이 섞여 있다. "
                "자기 확인은 항상 일치하므로 측정이 아니라 항등식이다."
            )
            raise SelfCorroborationError(msg)

        loc = finding.location
        near = [
            (p, ln)
            for p, ln in self._hits
            if p == loc.path
            and loc.span.overlaps(ln - self.line_slack, ln + self.line_slack)
        ]
        if near:
            who = "+".join(sorted(self._sources))
            return Evidence(
                kind=EvidenceKind.CORROBORATION,
                verdict=Verdict.SUPPORTS,
                detail=f"{who} 도 {loc.path}:{near[0][1]} 를 지적했다",
                locator=f"{loc.path}:{near[0][1]}",
            )

        return Evidence(
            kind=EvidenceKind.CORROBORATION,
            verdict=Verdict.INCONCLUSIVE,
            detail=(
                "확인자가 이 자리를 지적하지 않았다 - "
                "동의가 없는 것이지 반증된 것이 아니다"
            ),
        )

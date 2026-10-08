"""교차 확인 채점자 - 「다른 독립 도구가 동의하면 맞다」 정의.

세 번째 정답 정의다. 앞의 둘과 성질이 다르다:

  ProvableSafety  - 사람이 쓴 안전 근거가 기준        (증거 기반)
  InjectedDefect  - 주입한 결함 위치가 기준            (구성 기반)
  Corroboration   - **다른 독립 도구의 동의**가 기준    (합의 기반)

🔴 채점자는 **증거를 수집하지 않고 받는다.** verify/ 의 CorroborationVerifier 와
   같은 원칙이다. 분석기를 들고 샘플마다 돌리면
   - eval/ 이 analysis/ 에 묶이고
   - [실측] 30 샘플에 15초가 든다 (일괄로 미리 계산하면 0.5초)

🔴 그리고 확인자는 평가 대상과 **반드시 달라야** 한다. 같으면 자기 채점이고,
   항상 일치하므로 측정이 아니라 항등식이다. SelfCorroborationError 가 막는다.

⚠ 한계를 명시한다 - 합의는 정확성의 약한 대리지표다. 두 린터가 같은 줄을
  지적해도 둘 다 틀렸을 수 있다. 그래서 **세 정의 중 하나로만** 쓰고
  단독 진실값으로 쓰지 않는다. FALSE_POSITIVE 를 낼 수 없는 것도 그 때문이다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import MATCH_POLICY, Judgment, Outcome

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.location import Span
    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.sample import LabeledSample


def _order(hit: tuple[str, Span]) -> tuple[str, int, int]:
    path, span = hit
    return path, span.start.line, span.end.line if span.end is not None else span.start.line


class SelfCorroborationError(ValueError):
    """평가 대상이 자기 자신을 확인하려 했다.

    같은 도구의 지적을 같은 도구로 확인하면 항상 일치한다 -
    측정이 아니라 항등식이다.
    """


class StaticCorroborationGrader:
    """독립 도구가 같은 자리를 지적했는가로 판정한다."""

    name = "static_corroboration"
    definition = "독립 분석기가 같은 위치를 지적하면 TP, 아니면 판정 불가 (합의 기반)."
    # 🔴 FALSE_POSITIVE 가 없다. 동의가 없는 것은 반증이 아니므로
    #    이 정의로는 「틀렸다」를 말할 수 없다.
    emits = frozenset({Outcome.TRUE_POSITIVE, Outcome.UNDECIDABLE})
    uses_llm_judge = False

    def __init__(
        self,
        reference: Mapping[str, Sequence[Finding]],
        reference_name: str = "reference",
        line_slack: int = 2,
    ) -> None:
        """Args:
        reference: 샘플 id -> 확인자의 지적. **미리 일괄로 계산해 넘긴다.**
        reference_name: 확인자 이름. 설정 지문과 사유 문구에 쓰인다.
        line_slack: 몇 줄까지 "같은 자리" 로 볼지. 🔴 손잡이다.
        """
        if line_slack < 0:
            msg = f"line_slack 은 0 이상이다: {line_slack}"
            raise ValueError(msg)
        self.line_slack = line_slack
        self.reference_name = reference_name
        # 🔴 참조도 보고 범위째 든다 - 시작 줄만 남기면 방향마다 판정이 갈린다 (Span.near · A2a)
        self._hits: dict[str, tuple[tuple[str, Span], ...]] = {
            sid: tuple(sorted({(f.location.path, f.location.span) for f in fs}, key=_order))
            for sid, fs in reference.items()
        }
        self._sources = frozenset(
            f.source for fs in reference.values() for f in fs
        )

    def config_signature(self) -> str:
        return (
            f"{self.name}(ref={self.reference_name},"
            f"slack={self.line_slack},match={MATCH_POLICY})"
        )

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        if not observed:
            return []

        sources = {o.finding.source for o in observed}
        if self._sources & sources:
            msg = (
                f"확인자에 평가 대상({sorted(sources & self._sources)})의 지적이 "
                "섞여 있다. 자기 채점은 항상 일치하므로 측정이 아니라 항등식이다."
            )
            raise SelfCorroborationError(msg)

        hits = self._hits.get(sample.sample_id, ())
        return [self._judge_one(o, hits) for o in observed]

    def _judge_one(
        self, o: ObservedFinding, hits: tuple[tuple[str, Span], ...]
    ) -> Judgment:
        loc = o.finding.location
        near = [
            span.start.line
            for path, span in hits
            if path == loc.path and loc.span.near(span, self.line_slack)
        ]
        if near:
            return Judgment(
                finding_key=o.finding.fingerprint,
                outcome=Outcome.TRUE_POSITIVE,
                grader=self.name,
                rationale=(
                    f"{self.reference_name} 도 {loc.path}:{near[0]} 를 지적했다"
                ),
            )

        # 🔴 동의가 없다고 틀린 것은 아니다. 확인자가 그 층을 안 볼 수도 있다.
        #    (실측: Ruff 는 S602 를 보지만 mypy 에는 보안 규칙 자체가 없다)
        return Judgment(
            finding_key=o.finding.fingerprint,
            outcome=Outcome.UNDECIDABLE,
            grader=self.name,
            rationale=(
                f"{self.reference_name} 는 이 자리를 지적하지 않았다 - "
                "동의가 없는 것이지 반증된 것이 아니다"
            ),
        )

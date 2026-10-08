"""주입 결함 채점자 - Qodo 정의를 충실히 구현한다.

**이 채점자는 일부러 「덜 정직한」 정의다.** 우리가 비판하는 정의를
비판만 하는 게 아니라 **구현해서 나란히 세우는 것**이 이 프로젝트의 논지이기 때문이다.

Qodo Code Review Benchmark 의 정의:
  - 결함을 주입한 자리와 일치하면 Hit (설명 + 파일·라인 모두 맞아야 함)
  - 그 외는 전부 miss
  - 🔴 **결함 없는 코드 위의 지적은 무조건 FP** - 「판정 불가」라는 칸이 없다

ProvableSafetyGrader 와 비교하면 차이가 정확히 한 군데다:

    안전 근거가 덮는 범위 **밖**의 지적
      ProvableSafety -> UNDECIDABLE   (판정할 수 없다)
      InjectedDefect -> FALSE_POSITIVE (틀렸다)

같은 지적, 다른 정의, 다른 숫자. **그 편차가 이 플랫폼의 산출물이다.**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import MATCH_POLICY, Judgment, Outcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.sample import LabeledSample


class InjectedDefectGrader:
    """주입한 결함과 일치하는가만 본다."""

    name = "injected_defect"
    definition = "주입 결함 위치와 일치하면 TP, 그 외 전부 FP. 판정 불가 없음 (Qodo 정의)."
    emits = frozenset({Outcome.TRUE_POSITIVE, Outcome.FALSE_POSITIVE})
    uses_llm_judge = False

    def __init__(self, line_slack: int = 0) -> None:
        if line_slack < 0:
            msg = f"line_slack 은 0 이상이다: {line_slack}"
            raise ValueError(msg)
        self.line_slack = line_slack

    def config_signature(self) -> str:
        return f"{self.name}(slack={self.line_slack},match={MATCH_POLICY})"

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        return [self._judge_one(sample, o) for o in observed]

    def _judge_one(self, sample: LabeledSample, o: ObservedFinding) -> Judgment:
        loc = o.finding.location
        key = o.finding.fingerprint

        for i, defect in enumerate(sample.defects):
            d = defect.location
            if d.path == loc.path and loc.span.near(d.span, self.line_slack):  # A2a - 같은 함수
                return Judgment(
                    finding_key=key,
                    outcome=Outcome.TRUE_POSITIVE,
                    grader=self.name,
                    matched_defect=f"{sample.sample_id}#d{i}",
                    rationale=f"주입 결함 {d.path}:{d.line} 와 일치 (slack {self.line_slack})",
                )

        # 🔴 이 정의에는 「판정 불가」가 없다.
        #    결함 목록에 없으면 그냥 틀린 것으로 친다 - 그게 이 정의의 성질이고,
        #    ProvableSafetyGrader 와의 편차가 정확히 여기서 생긴다.
        reason = (
            "결함 없는 코드 위의 지적"
            if sample.is_negative
            else "주입 결함 위치와 일치하지 않음"
        )
        return Judgment(
            finding_key=key,
            outcome=Outcome.FALSE_POSITIVE,
            grader=self.name,
            rationale=f"{reason} - 이 정의는 판정 불가를 두지 않는다",
        )

"""증명된 안전 채점자 - 이 프로젝트의 차별점.

**"Clean PR 에 지적이 나오면 FP"** 와 무엇이 다른가:

  기존 문헌: "아무도 코멘트를 안 달았다" = 증거의 부재
            → 사람이 놓친 진짜 버그를 모델이 잡으면 FP 로 오채점된다.

  여기    : "왜 안전한지 서면 근거가 있다" = 부재의 증거
            → 여기서의 FP 는 진짜 FP 다.

그리고 근거는 **특정 주장**을 덮는다. 범위 밖의 지적까지 FP 로 접으면
판정 불가를 오답으로 채점하는 것이고, 그건 우리가 비판하는 바로 그 짓이다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Judgment, Outcome

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.sample import LabeledSample


class ProvableSafetyGrader:
    """서면 안전 근거와 대조한다. LLM 판정자를 쓰지 않는다."""

    name = "provable_safety"
    definition = (
        "서면 안전 근거가 덮는 범위 안의 **결함 주장**은 FP. "
        "범위 밖이거나 관례 주장이면 판정 불가."
    )
    emits = frozenset({Outcome.TRUE_POSITIVE, Outcome.FALSE_POSITIVE, Outcome.UNDECIDABLE})
    uses_llm_judge = False

    def __init__(self, overlap_slack: int = 0) -> None:
        """Args:
        overlap_slack: 덮는 범위를 위아래로 몇 줄 늘릴지.
            🔴 이것도 측정 손잡이다 - 늘리면 FP 가 늘어난다. 기본 0.
        """
        if overlap_slack < 0:
            msg = f"overlap_slack 은 0 이상이다: {overlap_slack}"
            raise ValueError(msg)
        self.overlap_slack = overlap_slack

    def config_signature(self) -> str:
        return f"{self.name}(slack={self.overlap_slack})"

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        if sample.is_proven_safe:
            return [self._judge_negative(sample, o) for o in observed]
        return [self._judge_positive(sample, o) for o in observed]

    def _judge_negative(
        self, sample: LabeledSample, o: ObservedFinding
    ) -> Judgment:
        """증명된 음성 위의 지적."""
        assert sample.safety is not None  # is_proven_safe 가 보장
        loc = o.finding.location
        covered = sample.safety.covered_lines

        # 🔴 관례 주장은 안전 근거가 **반박할 수 없다.**
        #    근거는 "이 결함처럼 보이는 것이 왜 결함이 아닌가"를 말한다.
        #    "docstring 이 없다"는 그 범위 밖이고, 더구나 **사실이다**.
        #    [실측] 이 구분을 빼먹었을 때 FP 66건 중 45건이 D103 이었다 -
        #    맞는 지적을 오답으로 채점한 것이고, 그건 우리가 비판하는 오류다.
        if not o.finding.category.is_defect_claim:
            return Judgment(
                finding_key=o.finding.fingerprint,
                outcome=Outcome.UNDECIDABLE,
                grader=self.name,
                rationale=(
                    f"{o.finding.rule_id} 는 관례 주장이다 "
                    f"({o.finding.category.value}) - 안전 근거는 결함 주장만 "
                    "반박할 수 있으므로 이 채점자의 정의로는 판정할 수 없다"
                ),
            )

        if covered is not None and sample.safety.covered_path == loc.path:
            lo = max(1, covered[0] - self.overlap_slack)
            hi = covered[1] + self.overlap_slack
            if lo <= loc.line <= hi:
                return Judgment(
                    finding_key=o.finding.fingerprint,
                    outcome=Outcome.FALSE_POSITIVE,
                    grader=self.name,
                    rationale=(
                        f"서면 근거가 {loc.path}:{covered[0]}-{covered[1]} 를 덮는다. "
                        f"근거: {sample.safety.claim}"
                    ),
                )

        # 🔴 범위 밖은 FP 가 아니다. 이 채점자는 판정할 수 없다.
        return Judgment(
            finding_key=o.finding.fingerprint,
            outcome=Outcome.UNDECIDABLE,
            grader=self.name,
            rationale=(
                f"{loc.path}:{loc.line} 는 안전 근거가 덮는 범위 밖이다 - "
                "이 채점자의 정의로는 참/거짓을 말할 수 없다"
            ),
        )

    def _judge_positive(
        self, sample: LabeledSample, o: ObservedFinding
    ) -> Judgment:
        """진짜 결함이 있는 샘플(twin) 위의 지적."""
        loc = o.finding.location
        for i, defect in enumerate(sample.defects):
            d = defect.location
            if d.path != loc.path:
                continue
            lo = max(1, d.span.start.line - self.overlap_slack)
            hi = (d.span.end.line if d.span.end else d.span.start.line) + self.overlap_slack
            if lo <= loc.line <= hi:
                return Judgment(
                    finding_key=o.finding.fingerprint,
                    outcome=Outcome.TRUE_POSITIVE,
                    grader=self.name,
                    matched_defect=f"{sample.sample_id}#d{i}",
                    rationale=f"결함 위치 {d.path}:{lo}-{hi} 와 겹친다",
                )

        # 결함이 있는 샘플의 다른 지점 지적은, 이 채점자로는 알 수 없다.
        # 정답 라벨이 그 지점을 말하지 않기 때문이다.
        return Judgment(
            finding_key=o.finding.fingerprint,
            outcome=Outcome.UNDECIDABLE,
            grader=self.name,
            rationale=f"{loc.path}:{loc.line} 에 대한 정답 라벨이 없다",
        )

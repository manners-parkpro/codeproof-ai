"""짝 기반 채점자 - 「구별했는가」를 채점 단계에서 묻는다.

🔴 이것이 `pairing.score_pairs()` 와 다른 층이다.

  `score_pairs()`  - 기존 채점자의 판정을 **사후 요약**한다.
                     자기만의 정답 정의가 없다.
  `PairedFixGrader` - **정답 정의 자체**다. 「짝에도 같은 지적이 있으면
                     탐지의 증거가 아니다」.

[실측] 그 차이가 숫자에 남는다. `D002#twin` 의 S602 는 안전한 쪽에도 똑같이
나오는데, InjectedDefectGrader 는 결함 위치와 겹치므로 **TP** 를 준다.
짝 요약은 그 쌍을 P-V 로 표시하지만 **per-finding Precision 은 오염된 채**다.
이 채점자는 그걸 채점 단계에서 막는다.

⚠ 「짝에도 있다」를 FALSE_POSITIVE 로 접지 않는다. 그 지적은 **틀린 게 아니라
  변별력이 없는** 것이다 - 진짜 결함을 가리키고는 있다. 틀림과 무정보를
  섞으면 우리가 비판하는 그 오류가 된다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from codeproof_ai.eval.grading.base import Judgment, Outcome, UnboundGraderError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.location import Location
    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.sample import LabeledSample


class PairedFixGrader:
    """짝과 비교해 변별력이 있는 지적만 탐지로 인정한다."""

    name = "paired_fix"
    definition = (
        "짝에 없는 지적이 결함 위치와 겹치면 TP. "
        "짝에도 있으면 변별력 없음(판정 불가). "
        "음성 위의 **결함 주장**은 FP, 관례 주장은 판정 불가."
    )
    emits = frozenset({Outcome.TRUE_POSITIVE, Outcome.FALSE_POSITIVE, Outcome.UNDECIDABLE})
    uses_llm_judge = False

    def __init__(self, line_slack: int = 0) -> None:
        if line_slack < 0:
            msg = f"line_slack 은 0 이상이다: {line_slack}"
            raise ValueError(msg)
        self.line_slack = line_slack
        # 🔴 None 으로 시작한다. 빈 dict 로 시작하면 bind_run 을 빼먹었을 때
        #    「짝에 아무 지적도 없다」로 읽혀 **전부 TP** 가 된다 - 조용히, 예외 없이.
        #    실제로 run_analyzer·run_provider 가 그렇게 채점하고 있었다.
        self._by_sample: dict[str, tuple[Finding, ...]] | None = None

    def config_signature(self) -> str:
        return f"{self.name}(slack={self.line_slack})"

    def bind_run(self, findings_by_sample: Mapping[str, Sequence[Finding]]) -> None:
        """🔴 실행 전체의 지적을 받는다 (runner 가 채점 직전에 호출).

        짝의 지적을 알아야 하므로 샘플 하나만 보고는 채점할 수 없다.
        """
        self._by_sample = {k: tuple(v) for k, v in findings_by_sample.items()}

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        if self._by_sample is None:
            msg = (
                f"{self.name} 은 실행 전체의 지적이 있어야 채점한다. "
                "러너가 bind_run() 을 부르지 않았다 - run_reviewer 를 거쳐 돌려라."
            )
            raise UnboundGraderError(msg)
        counterpart = self._by_sample.get(sample.paired_with or "", ())
        return [self._judge_one(sample, o, counterpart) for o in observed]

    def _judge_one(
        self,
        sample: LabeledSample,
        o: ObservedFinding,
        counterpart: Sequence[Finding],
    ) -> Judgment:
        key = o.finding.fingerprint
        loc = o.finding.location

        if sample.is_negative:
            # 🔴 관례 주장은 거짓 경보가 아니다 - "docstring 이 없다"는 사실이다.
            #    이 구분 없이 세면 룰 선택이 곧 FP 수가 된다 (provable_safety 와
            #    같은 결함이었다: FP 66건 중 45건이 D103).
            if not o.finding.category.is_defect_claim:
                return Judgment(
                    finding_key=key,
                    outcome=Outcome.UNDECIDABLE,
                    grader=self.name,
                    rationale=(
                        f"{o.finding.rule_id} 는 관례 주장이다 - "
                        "안전한 코드 위에 나와도 틀린 지적이 아니다"
                    ),
                )
            # 안전한 코드 위의 결함 주장은 짝과 무관하게 거짓 경보다.
            return Judgment(
                finding_key=key,
                outcome=Outcome.FALSE_POSITIVE,
                grader=self.name,
                rationale="증명된 음성 위의 결함 주장",
            )

        matched = self._matching_defect(sample, loc)
        if matched is None:
            return Judgment(
                finding_key=key,
                outcome=Outcome.UNDECIDABLE,
                grader=self.name,
                rationale=f"{loc.path}:{loc.line} 에 대한 정답 라벨이 없다",
            )

        twin_of = self._appears_in(o.finding, counterpart)
        if twin_of is not None:
            # 🔴 틀린 게 아니라 **변별력이 없다.** 짝에도 같은 지적을 냈다면
            #    그 지적이 결함을 가리켰다는 증거가 아니다.
            return Judgment(
                finding_key=key,
                outcome=Outcome.UNDECIDABLE,
                grader=self.name,
                matched_defect=matched,
                rationale=(
                    f"짝({sample.paired_with})에도 같은 지적이 있다 "
                    f"({twin_of}) - 결함을 가려낸 증거가 아니다"
                ),
            )

        return Judgment(
            finding_key=key,
            outcome=Outcome.TRUE_POSITIVE,
            grader=self.name,
            matched_defect=matched,
            rationale="짝에 없고 결함 위치와 겹친다 - 구별했다",
        )

    def _matching_defect(
        self, sample: LabeledSample, loc: Location
    ) -> str | None:
        for i, defect in enumerate(sample.defects):
            d = defect.location
            if d.path != loc.path:
                continue
            lo = max(1, d.span.start.line - self.line_slack)
            hi = (
                d.span.end.line if d.span.end else d.span.start.line
            ) + self.line_slack
            if lo <= loc.line <= hi:
                return f"{sample.sample_id}#d{i}"
        return None

    def _appears_in(
        self, finding: Finding, counterpart: Sequence[Finding]
    ) -> str | None:
        """같은 지적이 짝에도 있는가.

        경로가 다르므로(decoy.py vs twin.py) fingerprint 로 비교할 수 없다 -
        **룰과 둘러싼 심볼**로 본다. 같은 룰이 같은 함수에서 양쪽 다 나오면
        그 지적은 두 버전을 구별하지 못한 것이다.
        """
        want = (finding.rule_id, finding.location.symbol)
        for other in counterpart:
            if (other.rule_id, other.location.symbol) == want:
                return f"{other.location.path}:{other.location.line}"
        return None

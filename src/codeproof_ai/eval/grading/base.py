"""채점자 확장점 — 이 프로젝트 논지의 핵심.

같은 Finding[] 을 여러 채점자에 통과시키고 **편차를 헤드라인으로 낸다.**
발표된 Precision 이 정답 정의에 따라 20배 차이 나는데
아무도 그 편차를 측정하지 않았다는 것이 이 프로젝트의 빈칸이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codeproof_ai.domain.observation import ObservedFinding
    from codeproof_ai.eval.sample import LabeledSample


class UnboundGraderError(RuntimeError):
    """실행 문맥이 필요한 채점자를 문맥 없이 돌렸다.

    🔴 조용히 기본값으로 채점하면 안 되는 종류의 오류다. 짝 기반 채점자가
    빈 짝을 「짝에 지적이 없다」로 읽으면 전부 TP 가 되는데, 그건 틀린 숫자가
    아니라 **틀렸다는 것을 알 수 없는 숫자**다.
    """


class Outcome(StrEnum):
    """지적 1건에 대한 채점 결과."""

    TRUE_POSITIVE = "tp"
    FALSE_POSITIVE = "fp"
    UNDECIDABLE = "undecidable"
    """이 채점자의 정의로는 판정할 수 없다.

    🔴 FP 로 접지 않는다. 기존 문헌이 바로 이 지점에서 틀렸다 —
       "아무도 코멘트 안 함" 을 "틀림" 으로 채점해서,
       사람이 놓친 진짜 버그를 FP 로 만들었다.
    """


@dataclass(frozen=True, slots=True)
class Judgment:
    """한 채점자의 한 **고유 지적**에 대한 판정.

    출현 빈도는 여기 없다 - 판정은 빈도와 무관해야 하고,
    빈도는 ObservedFinding 이 들고 있다가 집계 시점에 결합된다.
    """

    finding_key: str
    """관측을 묶은 그룹핑 키. ObservationSet.grouper 정책에 따라 달라진다."""

    outcome: Outcome
    grader: str
    matched_defect: str | None = None
    rationale: str = ""


@runtime_checkable
class Grader(Protocol):
    """하나의 "정답 정의" 를 구현한다.

    구현체는 자기가 **무엇을 정답으로 보는지** 를 명시해야 한다.
    그게 이 플랫폼이 측정하려는 변수다.
    """

    name: str

    definition: str
    """정답 정의를 한 문장으로. 리포트에 그대로 인쇄된다.

    예: "리뷰 후 개발자가 실제로 고친 것과 일치" (Martian 정의)
    """

    emits: frozenset[Outcome]
    """🔴 이 채점자가 **낼 수 있는** 판정의 어휘.

    채점자마다 어휘가 다르다. 예컨대 합의 기반 채점자는 FP 를 낼 수 없다 -
    동의가 없는 것은 반증이 아니기 때문이다.

    어휘가 다른 채점자의 FP 수를 그냥 나란히 놓으면 **범주 차이를 편차로
    오해**하게 된다. 편차 계산은 같은 어휘를 가진 채점자끼리만 한다.
    """

    uses_llm_judge: bool
    """🔴 LLM 판정자를 쓰는가.

    True 면 리포트에 κ·위치편향·자기선호 측정이 **의무적으로** 따라붙는다 (E3).
    코드 도메인의 판정자 일치도는 전 도메인 최악이다
    (pairwise κ 0.159 / Fleiss κ 0.070).
    """

    def judge(
        self, sample: LabeledSample, observed: Sequence[ObservedFinding]
    ) -> list[Judgment]:
        """관측된 지적들을 채점한다.

        🔴 **고유 지적당 한 번만** 채점한다. 출현 빈도로 자르지 않는다.
           임계값(k회 이상)은 채점이 아니라 **집계 시점**에 건다 -
           그래야 k 를 스윕해도 재채점이 필요 없고, 채점 비용이 임계값 수에
           비례해 늘지 않는다.

        구현 규약:
        - 판정 불가는 UNDECIDABLE 로 낸다. FP 로 접지 않는다.
        - 음성 샘플(sample.is_negative)에서의 지적은 이 채점자의 정의상
          FP 인지 UNDECIDABLE 인지 **명시적으로** 결정한다.
        - ObservedFinding.rate 를 판정에 쓰지 않는다. 자기일관성은
          정확성이 아니다 - 그 둘의 관계는 측정 대상이지 가정이 아니다.
        """
        ...

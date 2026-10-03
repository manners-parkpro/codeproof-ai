"""정답 라벨이 붙은 평가 샘플.

🔴 이 모듈은 eval/ 안에만 존재한다.
   런타임(analysis·llm·verify)은 eval/ 을 import 할 수 없으므로
   라벨을 볼 방법이 구조적으로 없다. 예전에는 domain 에 두고 테스트로
   단속했는데, 테스트로 지키는 불변식은 구조가 약하다는 신호였다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeproof_ai.domain.location import Location
    from codeproof_ai.domain.target import ReviewTarget


class Stratum(StrEnum):
    """코퍼스 층.

    🔴 층을 섞어서 집계하지 않는다 (CLAUDE.md E2).
       Recall 은 A·B 각각, FPR 은 C·D 각각으로 보고한다.
    """

    SYNTHETIC = "A"
    """변이 주입. recall **바닥선** 전용 - 현실성을 주장하지 않는다."""

    PAIRED_FIX = "B"
    """양성의 수정된 버전. 같은 함수, 가드만 다르다. 과잉지적 측정용."""

    CLEAN_PR = "C"
    """매칭된 무결함 PR. 기존 문헌과의 비교 가능성 확보용 (v2)."""

    DECOY = "D"
    """수제 near-miss. 버그처럼 보이지만 **증명 가능하게 안전**하다."""


class DefectOrigin(StrEnum):
    """정답 라벨의 출처. 어느 채점자가 이 샘플을 쓸 수 있는지 결정한다."""

    INJECTED = "injected"
    MINED_FIX = "mined_fix"
    HUMAN_REVIEW = "human_review"
    EXECUTION = "execution"


@dataclass(frozen=True, slots=True)
class Defect:
    """정답 결함 1건."""

    location: Location
    origin: DefectOrigin
    description: str
    category: str | None = None
    fix_diff: str | None = None


@dataclass(frozen=True, slots=True)
class SafetyRationale:
    """decoy 가 왜 안전한지에 대한 서면 근거.

    🔴 이것이 없으면 D층 음성 라벨이 성립하지 않는다 (CLAUDE.md K2).

    근거 없는 decoy 는 그냥 "아무도 확인 안 한 코드" 이고,
    그건 이 프로젝트가 비판하는 바로 그것 - 증거의 부재를 부재의 증거로
    착각하는 것 - 과 같아진다.
    """

    claim: str
    justification: str
    guard_location: Location | None = None
    buggy_twin_id: str | None = None
    covered_path: str | None = None
    covered_lines: tuple[int, int] | None = None
    """🔴 이 주장이 **덮는 범위**.

    안전 근거는 특정 주장을 덮는다 - "9행의 shell=True 는 안전하다".
    같은 파일 30행의 무관한 결함까지 덮지는 않는다.

    범위 밖의 지적을 FP 로 접으면 우리가 비판한 바로 그 짓이 된다 -
    판정 불가를 오답으로 채점하는 것. 그래서 밖은 UNDECIDABLE 로 낸다.
    """

    shape: str | None = None
    """가드를 찾으려면 어디를 봐야 하는가(`GuardShape`). **분류와 직교하는 축**이다.

    🔴 손으로 적지 않는다 - `guard_symbol` 과 소스에서 **도출**된다.
       적게 하면 틀리고, 틀려도 아무도 모른다.
    """

    category: str | None = None
    """🔴 미끼 분류(`TrapKind`). **음성 쪽에도 실어야 한다.**

    전에는 분류가 twin(양성)의 `Defect.category` 에만 있었다. FPR 은 음성에서
    재는데 음성이 분류를 모르면 **분류별 FPR 을 낼 수 없다** - 코퍼스 구성비가
    집계를 얼마나 움직이는지(`eval/mix.py`)를 측정할 수 없게 된다.
    """

    def __post_init__(self) -> None:
        if not self.justification.strip():
            msg = "decoy 에는 서면 안전 근거가 반드시 있어야 한다 (K2)"
            raise ValueError(msg)
        if self.covered_lines is not None:
            lo, hi = self.covered_lines
            if lo < 1 or hi < lo:
                msg = f"covered_lines 가 잘못됐다: {self.covered_lines}"
                raise ValueError(msg)


# 짝 채점이 성립하는 층. 두 층 모두 "가드만 다른" 쌍으로 구성된다.
_PAIRED_STRATA = frozenset({Stratum.PAIRED_FIX, Stratum.DECOY})


@dataclass(frozen=True, slots=True)
class LabeledSample:
    """리뷰 대상 + 정답 라벨.

    Attributes:
        target: 리뷰어에게 제시되는 것. 라벨은 여기 없다.
        stratum: 소속 층.
        defects: 정답 결함. 음성 샘플이면 빈 튜플.
        safety: 증명된 음성의 서면 안전 근거. defects 와 상호 배타.
        paired_with: 짝이 되는 샘플 id. B·D 층 필수 - 짝 채점의 전제다.
    """

    target: ReviewTarget
    stratum: Stratum
    defects: tuple[Defect, ...] = field(default_factory=tuple)
    safety: SafetyRationale | None = None
    paired_with: str | None = None

    def __post_init__(self) -> None:
        sid = self.target.target_id

        # 🔴 층과 무관한 근본 불변식: 결함이 있거나 안전 근거가 있거나, 둘 다는 아니다.
        #    "결함이 있는데 안전하다" 는 표현 자체가 모순이다.
        if self.defects and self.safety is not None:
            msg = f"{sid}: defects 와 safety 는 상호 배타다 - 양성이면서 증명된 음성일 수 없다"
            raise ValueError(msg)

        # D층 **음성**(decoy) 에만 안전 근거를 요구한다.
        # D층 **양성**(twin) 은 결함을 들고 안전 근거가 없다.
        if self.stratum is Stratum.DECOY and not self.defects and self.safety is None:
            msg = f"{sid}: D층 음성에는 SafetyRationale 이 필수다 (K2)"
            raise ValueError(msg)

        # 짝 채점(PrimeVul P-C/P-V/P-B/P-R)은 짝이 있어야 성립한다.
        if self.stratum in _PAIRED_STRATA and self.paired_with is None:
            msg = f"{sid}: {self.stratum.name} 층은 짝이 되는 샘플 id 가 필수다"
            raise ValueError(msg)

    @property
    def sample_id(self) -> str:
        return self.target.target_id

    @property
    def is_proven_safe(self) -> bool:
        """서면 근거로 안전이 **증명된** 음성인가.

        "아무도 코멘트 안 함"(증거의 부재) 과 구별된다.
        이 구분이 이 프로젝트의 기여이므로 타입 수준에서 드러낸다.
        """
        return self.safety is not None

    @property
    def is_negative(self) -> bool:
        """음성 샘플인가 - 즉 여기서의 지적은 전부 FP 인가."""
        return not self.defects

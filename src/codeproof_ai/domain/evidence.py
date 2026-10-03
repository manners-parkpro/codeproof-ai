"""근거(Evidence) — 런타임 검증 산출물.

🔴 이 모듈은 정답 라벨을 모른다 (CLAUDE.md I2).
   Verification 은 라벨 없이 돌아야 하는 제품 기능이고,
   정답 대조는 eval/ 의 Grader 이 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeproof_ai.domain.finding import Finding


class EvidenceKind(StrEnum):
    """검증 종류."""

    CITATION = "citation"
    """모델이 인용한 코드가 해당 위치에 실제로 존재하는가."""

    GUARD = "guard"
    """주장한 실패를 막는 방어 코드가 이미 있는가."""

    CORROBORATION = "corroboration"
    """정적분석기가 같은 지점을 독립적으로 지적했는가."""

    REACHABILITY = "reachability"
    """해당 코드가 엔트리포인트에서 도달 가능한가.

    v1 은 모듈 단위까지만 본다 — 파이썬 전용 호출그래프 도구가 전멸했다
    (CLAUDE.md T3).
    """


class Verdict(StrEnum):
    """검증 결과.

    SUPPORTS / REFUTES 와 별개로 INCONCLUSIVE 를 둔다.
    "확인 못 함" 을 "반박됨" 으로 접으면 confidence 가 조용히 왜곡된다.
    """

    SUPPORTS = "supports"
    REFUTES = "refutes"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class Evidence:
    """단일 검증 결과.

    Attributes:
        kind: 검증 종류.
        verdict: 판정.
        detail: 사람이 읽는 근거 설명.
        locator: 근거가 있는 위치 (있으면). 예: 가드가 발견된 행.
    """

    kind: EvidenceKind
    verdict: Verdict
    detail: str
    locator: str | None = None


@dataclass(frozen=True, slots=True)
class VerifiedFinding:
    """근거가 붙은 지적.

    confidence 는 Evidence 집계 결과다. 이 값이 "정답일 확률" 이 아니라는 점이
    중요하다 — 라벨을 보지 않고 계산했으므로 어디까지나 **근거의 양**이다.
    """

    finding: Finding
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"confidence 는 [0,1] 이다: {self.confidence}"
            raise ValueError(msg)

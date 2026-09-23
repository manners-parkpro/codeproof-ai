"""리뷰어 - 이 플랫폼의 1급 개념.

지적을 내는 것은 전부 리뷰어다. 정적분석기든 모델이든 에이전트든 사람이든,
**같은 하네스로 돌고 같은 채점을 받는다.** 그래야
"Ruff 가 0/10" 과 "Claude 가 N/10" 이 비교 가능한 숫자가 된다.

🔴 다만 **층(kind)이 다르면 섞어 집계하지 않는다.**
   에이전트는 파일 탐색·다회 턴·툴 사용이 가능하고 모델 API 는 아니다.
   같은 표에 놓되 층을 명시한다 - 이건 CLAUDE.md F3 과 같은 원칙이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget


class ReviewerKind(StrEnum):
    """리뷰어의 층. 🔴 섞어서 집계하면 안 되는 경계다."""

    STATIC = "static"
    """정적분석기. 결정적 - 같은 입력에 같은 출력."""

    MODEL_API = "model_api"
    """모델 API 직접 호출. 확률적. 툴 없음·단일 턴."""

    AGENT = "agent"
    """에이전트 CLI. 확률적. **툴 접근·다회 턴 가능** - model_api 와 층이 다르다."""

    IMPORTED = "imported"
    """외부에서 가져온 지적 (SARIF · JSON). 재생이므로 결정적."""

    HUMAN = "human"
    """사람 리뷰. 기준선이자 상한."""

    @property
    def is_deterministic(self) -> bool:
        """같은 입력에 같은 출력인가. 다회 샘플링의 의미가 여기서 갈린다."""
        return self in {ReviewerKind.STATIC, ReviewerKind.IMPORTED}


@dataclass(frozen=True, slots=True)
class ReviewTelemetry:
    """호출 1회의 비용·지연. 없는 항목은 None 으로 둔다 - 0 으로 채우지 않는다."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read: int | None = None
    reasoning_tokens: int | None = None
    ttft_ms: float | None = None
    total_ms: float | None = None
    refused: bool = False


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """리뷰어 1회 실행의 결과.

    Attributes:
        findings: 정규화된 지적.
        telemetry: 비용·지연. 정적분석기는 대부분 None 이다.
        raw: 🔴 원본. 정규화가 틀렸을 때의 유일한 근거다.
    """

    findings: tuple[Finding, ...]
    telemetry: ReviewTelemetry = field(default_factory=ReviewTelemetry)
    raw: dict[str, object] = field(default_factory=dict, repr=False)


@runtime_checkable
class Reviewer(Protocol):
    """지적을 내는 모든 것.

    구현 규약:
    - `review(target)` 는 **target.files 에 있는 것만** 본다. 실제 레포를 뒤지지 않는다.
      (분석기는 materialize 로, 모델은 프롬프트로 강제된다)
    - 부분 실패를 예외로 올리지 않는다. 1건이 깨져도 나머지를 살린다.
    - 원본을 `raw` 에 보존한다.

    선택적 메서드 (있으면 러너가 쓰고, 없으면 기본값을 쓴다):
    - `review_many(targets)` - 일괄 경로. 결정적 리뷰어만 의미가 있다.
      [실측] ruff 8.6배 · mypy 23.9배.
    - `manifest_fields()` - 🔴 매니페스트에 실을 항목을 **리뷰어가 신고한다**
      (`effort` · `cache_policy`). 러너가 짐작하면 모델 실행에 `effort="n/a"`
      같은 거짓말이 기록된다.
    - `tool_versions()` - 의존하는 외부 도구의 정확한 버전. ruff 는 pre-1.0 이라
      JSON 스키마가 바뀐다.
    """

    name: str
    kind: ReviewerKind
    identity: str
    """재현에 필요한 정확한 식별자. 도구는 `ruff/0.16.8`, 모델은 모델 ID."""

    def config_signature(self) -> str:
        """설정 지문. 매니페스트에 실린다."""
        ...

    def review(self, target: ReviewTarget) -> ReviewResult:
        """리뷰 1회. 확률적 리뷰어는 호출마다 다른 결과를 낼 수 있다."""
        ...

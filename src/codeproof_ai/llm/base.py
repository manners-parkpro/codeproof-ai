"""LLM 리뷰 확장점.

🔴 래퍼 라이브러리(LiteLLM·LangChain·instructor·PydanticAI)를
   이 패키지에 도입하지 않는다 (CLAUDE.md D1). 전부 OpenAI 모양 usage 로
   정규화하는데 벤더마다 토큰 정의가 달라서 텔레메트리가 손실된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from codeproof_ai.domain.finding import Finding
    from codeproof_ai.domain.target import ReviewTarget


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """벤더 차이를 흡수한 토큰 회계.

    🔴 total_input 계산이 벤더마다 다르다 (D2):
       Anthropic input_tokens 는 **마지막 캐시 breakpoint 이후만** 센다.
       OpenAI prompt_tokens 는 캐시를 포함한다.
       어댑터가 여기 넣기 전에 보정한다.
    """

    total_input: int
    """캐시 포함 전체 입력 토큰. 벤더 보정 후 값."""

    output: int
    """추론 토큰 포함 전체 출력 토큰."""

    cache_read: int = 0
    cache_write: int = 0
    reasoning: int | None = None
    """추론 토큰. 별도 보고 대상 — output 에 포함되지만 분리해서 남긴다."""

    def __post_init__(self) -> None:
        if self.total_input < 0 or self.output < 0:
            msg = "토큰 수는 음수가 될 수 없다"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ReviewResponse:
    """한 번의 리뷰 호출 결과.

    Attributes:
        findings: 정규화된 지적.
        usage: 토큰 회계.
        raw: 🔴 벤더 원본 응답 전체. 절대 버리지 않는다 (D1).
            정규화가 틀렸을 때 사후 재계산의 유일한 근거다.
        wire_schema: 🔴 실제로 전송된 스키마 (D5).
            Anthropic SDK 가 스키마를 조용히 재작성하므로
            Pydantic 모델이 아니라 이 값을 로깅해야 한다.
        request_id: 벤더 요청 id. 장애 보고용.
        ttft_ms: 첫 토큰까지 시간. 스트리밍에서 직접 잰 값만 넣는다 (F3 · DESIGN §7bis.2).
        total_ms: 전체 소요 시간.
    """

    findings: tuple[Finding, ...]
    usage: TokenUsage
    raw: dict[str, object] = field(default_factory=dict, repr=False)
    wire_schema: dict[str, object] = field(default_factory=dict, repr=False)
    request_id: str | None = None
    ttft_ms: float | None = None
    total_ms: float | None = None


@runtime_checkable
class ReviewProvider(Protocol):
    """한 벤더의 리뷰 호출을 감싼다."""

    name: str
    model_id: str
    """정확한 모델 ID. 별칭 금지 (D6)."""

    def review(
        self,
        target: ReviewTarget,
        *,
        effort: str,
        cache_nonce: str | None = None,
        stream: bool = False,
    ) -> ReviewResponse:
        """리뷰를 요청한다.

        Args:
            target: 리뷰 대상. **files 가 리뷰어가 볼 수 있는 전부**다 -
                여기 없는 코드는 모델에게 존재하지 않는다.
            effort: 🔴 필수. 기본값이 모델마다 다르다 (D4) —
                claude-opus-5-5 는 medium, claude-sonnet-5 는 high.
            cache_nonce: 캐시 무력화용 nonce. 🔴 프롬프트 **맨 앞**에 붙인다 (D3).
                캐싱은 prefix 매칭이라 뒤에 붙이면 무효다.
            stream: TTFT 를 재려면 True 여야 한다. 비스트리밍에서 유도 금지 (F3 · DESIGN §7bis.2).

        구현 규약:
        - max_retries=0. 재시도는 호출자가 센다.
        - 강제 tool use 를 쓰지 않는다 — 최신 Claude 에서 400 이다 (D5).
        - 출력 스키마는 평탄해야 한다 — Anthropic 은 재귀를 지원하지 않는다.
        """
        ...

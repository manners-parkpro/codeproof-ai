"""Anthropic 어댑터.

🔴 벤치마크 전용 설정 - 일반 애플리케이션과 다르다:

  max_retries=0     SDK 자동 재시도가 지연 측정을 오염시킨다. 직접 센다.
  fallbacks 없음    거부 시 다른 모델이 대신 답하면 **측정 대상이 바뀐다.**
                    refusal 은 감출 실패가 아니라 1급 데이터다.
  temperature 없음  Claude 4.7+ 에서 제거됐다. 보내면 400.
  강제 tool use 없음 최신 모델에서 400. output_config.format 을 쓴다.
  nonce 는 맨 앞     캐싱은 prefix 매칭이라 뒤에 붙이면 무효다.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from codeproof_ai.llm.base import ReviewResponse, TokenUsage
from codeproof_ai.llm.parse import parse_findings
from codeproof_ai.llm.render import load_prompt, render_user_message
from codeproof_ai.llm.schema import SCHEMA_NAME, review_schema

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget

DEFAULT_MODEL = "claude-fable-5-1"
DEFAULT_MAX_TOKENS = 16000


class AnthropicReviewProvider:
    """Anthropic Messages API 를 리뷰어로 쓴다."""

    name = "anthropic"

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        prompt_name: str = "review_v1",
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model_id = model_id
        self.prompt_name = prompt_name
        self.max_tokens = max_tokens
        self._system = load_prompt(prompt_name)
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """무인자 생성 - SDK 가 환경변수 -> OAuth 프로필 순으로 해결한다.

        어느 경로로 로그인하든 이 코드는 그대로다.
        """
        if self._client is None:
            # SDK 는 쓸 때 import 한다 - 맨 위에 두면 레지스트리를 거치는 모든 명령 · 가드가
            # 쓰지도 않는 SDK 를 읽는다 (0.8초 · openai 와 합쳐 1.1초 [실측: -X importtime]).
            import anthropic  # noqa: PLC0415 - 위 이유

            # 🔴 max_retries=0 - 재시도는 호출자가 세고, 지연 측정을 오염시키지 않는다.
            self._client = anthropic.Anthropic(max_retries=0)
        return self._client

    def config_signature(self) -> str:
        return f"anthropic({self.model_id},prompt={self.prompt_name})"

    def review(
        self,
        target: ReviewTarget,
        *,
        effort: str,
        cache_nonce: str | None = None,
        stream: bool = False,
    ) -> ReviewResponse:
        if not effort:
            msg = "effort 를 명시해야 한다 - 기본값이 모델마다 다르다 (D4)"
            raise ValueError(msg)

        client = self._get_client()
        schema = review_schema()
        params: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "system": self._system,
            "messages": [
                {"role": "user", "content": render_user_message(target, cache_nonce)}
            ],
            "output_config": {
                "effort": effort,
                "format": {
                    "type": "json_schema",
                    "name": SCHEMA_NAME,
                    "schema": schema,
                },
            },
        }

        started = time.perf_counter()
        ttft: float | None = None
        if stream:
            with client.messages.stream(**params) as s:
                for _ in s.text_stream:
                    if ttft is None:
                        ttft = (time.perf_counter() - started) * 1000
                    break
                message = s.get_final_message()
        else:
            message = client.messages.create(**params)
        total_ms = (time.perf_counter() - started) * 1000

        return self._to_response(message, target, schema, ttft, total_ms)

    def _to_response(
        self,
        message: Any,
        target: ReviewTarget,
        schema: dict[str, Any],
        ttft: float | None,
        total_ms: float,
    ) -> ReviewResponse:
        raw = message.model_dump() if hasattr(message, "model_dump") else dict(message)

        # 🔴 거부는 1급 데이터다. 감추지 않고 findings 0 + raw 에 기록한다.
        refused = getattr(message, "stop_reason", None) == "refusal"

        payload: dict[str, Any] = {"findings": []}
        if not refused:
            text = "".join(
                b.text for b in message.content if getattr(b, "type", "") == "text"
            )
            try:
                loaded = json.loads(text) if text.strip() else {}
                if isinstance(loaded, dict):
                    payload = loaded
            except json.JSONDecodeError:
                raw["_parse_error"] = "본문이 JSON 이 아니다"

        parsed = parse_findings(payload, source=self.name, target=target)
        raw["_rejected"] = list(parsed.rejected)
        raw["_refused"] = refused

        return ReviewResponse(
            findings=parsed.findings,
            usage=self._usage(message),
            raw=raw,
            # 🔴 Pydantic 모델이 아니라 **실제 전송된 스키마**를 남긴다 -
            #    SDK 가 미지원 제약을 조용히 제거하기 때문이다.
            wire_schema=schema,
            request_id=getattr(message, "_request_id", None),
            ttft_ms=ttft,
            total_ms=total_ms,
        )

    @staticmethod
    def _usage(message: Any) -> TokenUsage:
        """🔴 Anthropic 의 input_tokens 는 **마지막 캐시 breakpoint 이후만** 센다.

        공식 예시: 200k 캐시 문서 + 50토큰 질문 -> input_tokens: 50.
        보정 없이 OpenAI 의 prompt_tokens 와 더하면 범주 오류다 (D2).
        """
        u = getattr(message, "usage", None)
        if u is None:
            return TokenUsage(total_input=0, output=0)

        read = getattr(u, "cache_read_input_tokens", 0) or 0
        write = getattr(u, "cache_creation_input_tokens", 0) or 0
        plain = getattr(u, "input_tokens", 0) or 0

        details = getattr(u, "output_tokens_details", None)
        reasoning = None
        if details is not None:
            for field in ("reasoning_tokens", "reasoning"):
                value = getattr(details, field, None)
                if isinstance(value, int):
                    reasoning = value
                    break

        return TokenUsage(
            total_input=read + write + plain,
            output=getattr(u, "output_tokens", 0) or 0,
            cache_read=read,
            cache_write=write,
            reasoning=reasoning,
        )

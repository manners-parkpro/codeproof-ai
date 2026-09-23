"""OpenAI 어댑터.

Anthropic 과 대칭이되 벤더 차이를 반영한다:

  prompt_tokens     캐시를 **포함**한다 (Anthropic 은 제외) -> 보정 불필요
  캐싱              **기본 활성화, 해제 수단 없음** -> nonce 가 더 중요하다
  max_tokens        deprecated. max_completion_tokens 를 쓴다
  reasoning.effort  사다리가 다르다 (none/minimal 이 아래에 더 있다)
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import openai

from codeproof_ai.llm.base import ReviewResponse, TokenUsage
from codeproof_ai.llm.parse import parse_findings
from codeproof_ai.llm.render import load_prompt, render_user_message
from codeproof_ai.llm.schema import SCHEMA_NAME, review_schema

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget

DEFAULT_MODEL = "gpt-6-astra"
DEFAULT_MAX_TOKENS = 16000


class OpenAIReviewProvider:
    """OpenAI Chat Completions 를 리뷰어로 쓴다."""

    name = "openai"

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
        if self._client is None:
            self._client = openai.OpenAI(max_retries=0)
        return self._client

    def config_signature(self) -> str:
        return f"openai({self.model_id},prompt={self.prompt_name})"

    def review(
        self,
        target: ReviewTarget,
        *,
        effort: str,
        cache_nonce: str | None = None,
        stream: bool = False,  # noqa: ARG002 - 비스트리밍 경로만 우선 구현
    ) -> ReviewResponse:
        if not effort:
            msg = "effort 를 명시해야 한다 - 사다리가 벤더마다 다르다 (L4)"
            raise ValueError(msg)

        schema = review_schema()
        started = time.perf_counter()
        response = self._get_client().chat.completions.create(
            model=self.model_id,
            max_completion_tokens=self.max_tokens,
            reasoning_effort=effort,
            messages=[
                {"role": "system", "content": self._system},
                {"role": "user", "content": render_user_message(target, cache_nonce)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": SCHEMA_NAME,
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        total_ms = (time.perf_counter() - started) * 1000

        raw = (
            response.model_dump()
            if hasattr(response, "model_dump")
            else dict(response)
        )
        choice = response.choices[0] if response.choices else None
        refused = bool(getattr(getattr(choice, "message", None), "refusal", None))

        payload: dict[str, Any] = {"findings": []}
        if choice is not None and not refused:
            text = choice.message.content or ""
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
            usage=self._usage(response),
            raw=raw,
            wire_schema=schema,
            request_id=getattr(response, "_request_id", None),
            ttft_ms=None,
            total_ms=total_ms,
        )

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        """🔴 OpenAI 의 prompt_tokens 는 캐시를 **포함**한다 - 보정하지 않는다.

        Anthropic 쪽은 보정이 필요하다. 두 벤더를 같은 코드로 다루면 틀린다.
        """
        u = getattr(response, "usage", None)
        if u is None:
            return TokenUsage(total_input=0, output=0)

        details = getattr(u, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0 if details else 0
        out_details = getattr(u, "completion_tokens_details", None)
        reasoning = (
            getattr(out_details, "reasoning_tokens", None) if out_details else None
        )

        return TokenUsage(
            total_input=getattr(u, "prompt_tokens", 0) or 0,
            output=getattr(u, "completion_tokens", 0) or 0,
            cache_read=cached,
            reasoning=reasoning,
        )

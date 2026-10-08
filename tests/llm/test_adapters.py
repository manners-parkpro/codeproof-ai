"""모델 어댑터 - 자격증명 없이 검증 가능한 부분 전부.

🔴 실제 호출만 자격증명이 필요하다. **요청이 올바르게 조립되는지**,
   **응답이 올바르게 해석되는지**는 전부 여기서 검사한다.
   그래서 로그인하는 순간 바로 돌 것이라고 말할 수 있다.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.llm.anthropic_ import AnthropicReviewProvider
from codeproof_ai.llm.openai_ import OpenAIReviewProvider
from codeproof_ai.llm.render import render_user_message
from codeproof_ai.llm.schema import is_flat, review_schema, unsupported_keywords

TARGET = ReviewTarget(
    target_id="t", files=(SourceFile("m.py", "import os\nx = 1\n"),)
)

PAYLOAD = {
    "findings": [
        {
            "file": "m.py",
            "line_start": 1,
            "line_end": 1,
            "category": "correctness",
            "severity": "warning",
            "quoted_code": "import os",
            "message": "unused",
            "failure_mode": "아무 일도 안 일어난다",
        }
    ]
}


class TestSchemaPassesBothVendors:
    def test_no_recursion(self) -> None:
        """Anthropic 은 재귀 스키마를 지원하지 않는다."""
        assert is_flat(review_schema())

    def test_no_unsupported_keywords(self) -> None:
        assert unsupported_keywords(review_schema()) == set()

    def test_empty_findings_is_allowed(self) -> None:
        """🔴 「지적 없음」이 1급 답변이 아니면 모델이 뭐라도 만들어낸다."""
        assert "minItems" not in json.dumps(review_schema())

    def test_openai_strict_requirements(self) -> None:
        items = review_schema()["properties"]["findings"]["items"]
        assert items["additionalProperties"] is False
        assert set(items["required"]) == set(items["properties"])


class TestNoncePlacement:
    def test_nonce_is_at_the_very_front(self) -> None:
        """🔴 캐싱은 prefix 매칭 - 뒤에 붙이면 무효다."""
        body = render_user_message(TARGET, "abc123")
        assert body.startswith("<!-- run-nonce: abc123")

    def test_no_nonce_leaves_body_unchanged(self) -> None:
        assert render_user_message(TARGET, None) == render_user_message(TARGET, None)
        assert "run-nonce" not in render_user_message(TARGET, None)

    def test_line_numbers_are_rendered(self) -> None:
        """모델이 line_start 를 돌려줘야 하는데 번호 없이 세게 하면 오프바이원이 난다."""
        assert "   1 | import os" in render_user_message(TARGET, None)


class TestEffortIsMandatory:
    """🔴 기본값이 모델마다 다르다 - 명시 없이는 비교가 무효다."""

    @pytest.mark.parametrize(
        "provider",
        [AnthropicReviewProvider(), OpenAIReviewProvider()],
    )
    def test_empty_effort_is_refused(self, provider: Any) -> None:
        with pytest.raises(ValueError, match="effort"):
            provider.review(TARGET, effort="")


class TestAnthropicRequestShape:
    def _capture(self, provider: AnthropicReviewProvider) -> dict[str, Any]:
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(type="text", text=json.dumps(PAYLOAD))]
        msg.stop_reason = "end_turn"
        msg.usage = MagicMock(
            input_tokens=10,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=5,
            output_tokens=20,
            output_tokens_details=None,
        )
        msg.model_dump.return_value = {"id": "m1"}
        client.messages.create.return_value = msg
        provider._client = client
        provider.review(TARGET, effort="low", cache_nonce="N1")
        kwargs: dict[str, Any] = client.messages.create.call_args.kwargs
        return kwargs

    def test_effort_and_format_go_in_output_config(self) -> None:
        kw = self._capture(AnthropicReviewProvider())
        assert kw["output_config"]["effort"] == "low"
        assert kw["output_config"]["format"]["type"] == "json_schema"

    def test_no_temperature_is_sent(self) -> None:
        """Claude 4.7+ 에서 제거됐다 - 보내면 400."""
        kw = self._capture(AnthropicReviewProvider())
        assert "temperature" not in kw
        assert "top_p" not in kw

    def test_no_forced_tool_use(self) -> None:
        """최신 모델에서 400. LiteLLM 계열의 기본 경로가 여기서 죽는다."""
        kw = self._capture(AnthropicReviewProvider())
        assert "tool_choice" not in kw
        assert "tools" not in kw

    def test_no_fallbacks(self) -> None:
        """🔴 거부 시 다른 모델이 대신 답하면 측정 대상이 바뀐다."""
        kw = self._capture(AnthropicReviewProvider())
        assert "fallbacks" not in kw

    def test_nonce_leads_the_user_message(self) -> None:
        kw = self._capture(AnthropicReviewProvider())
        assert kw["messages"][0]["content"].startswith("<!-- run-nonce: N1")


class TestAnthropicResponseHandling:
    def _provider(self, msg: Any) -> AnthropicReviewProvider:
        p = AnthropicReviewProvider()
        client = MagicMock()
        client.messages.create.return_value = msg
        p._client = client
        return p

    def _msg(self, *, stop: str = "end_turn", text: str | None = None) -> Any:
        m = MagicMock()
        m.content = [MagicMock(type="text", text=text or json.dumps(PAYLOAD))]
        m.stop_reason = stop
        m.usage = MagicMock(
            input_tokens=10,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=5,
            output_tokens=20,
            output_tokens_details=None,
        )
        m.model_dump.return_value = {"id": "m1"}
        return m

    def test_input_tokens_are_corrected(self) -> None:
        """🔴 Anthropic 의 input_tokens 는 마지막 캐시 breakpoint 이후만 센다."""
        r = self._provider(self._msg()).review(TARGET, effort="low")
        assert r.usage.total_input == 115, "cache_read + cache_creation + input"
        assert r.usage.cache_read == 100

    def test_refusal_is_recorded_not_hidden(self) -> None:
        """🔴 거부는 감출 실패가 아니라 데이터다."""
        r = self._provider(self._msg(stop="refusal")).review(TARGET, effort="low")
        assert r.findings == ()
        assert r.raw["_refused"] is True

    def test_an_unreadable_body_is_counted_as_rejected(self) -> None:
        """🔴 JSON 이 아니거나 객체가 아닌 본문은 버린 이유로 센다 - 「지적 0건」과 다르다 (I)."""
        cases = (("not json", "본문이 JSON 이 아니다"), ("[]", "본문이 객체가 아니다 (list)"))
        for text, why in cases:
            r = self._provider(self._msg(text=text)).review(TARGET, effort="low")
            assert (r.findings, r.raw["_rejected"]) == ((), [why])

    def test_wire_schema_is_recorded(self) -> None:
        """🔴 SDK 가 스키마를 조용히 재작성하므로 전송된 것을 남긴다."""
        r = self._provider(self._msg()).review(TARGET, effort="low")
        assert r.wire_schema == review_schema()

    def test_findings_are_parsed(self) -> None:
        r = self._provider(self._msg()).review(TARGET, effort="low")
        assert len(r.findings) == 1
        assert r.findings[0].source == "anthropic"
        assert r.findings[0].quoted_code == "import os"


class TestOpenAIRequestShape:
    def _capture(self) -> dict[str, Any]:
        p = OpenAIReviewProvider()
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = json.dumps(PAYLOAD)
        choice.message.refusal = None
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage = MagicMock(
            prompt_tokens=120,
            completion_tokens=20,
            prompt_tokens_details=MagicMock(cached_tokens=100),
            completion_tokens_details=MagicMock(reasoning_tokens=5),
        )
        resp.model_dump.return_value = {"id": "r1"}
        client.chat.completions.create.return_value = resp
        p._client = client
        p.review(TARGET, effort="low", cache_nonce="N1")
        kwargs: dict[str, Any] = client.chat.completions.create.call_args.kwargs
        return kwargs

    def test_uses_max_completion_tokens(self) -> None:
        """max_tokens 는 deprecated 이고 추론 모델과 호환되지 않는다."""
        kw = self._capture()
        assert "max_completion_tokens" in kw
        assert "max_tokens" not in kw

    def test_strict_json_schema(self) -> None:
        kw = self._capture()
        assert kw["response_format"]["json_schema"]["strict"] is True

    def test_no_temperature(self) -> None:
        assert "temperature" not in self._capture()

    def test_effort_is_sent(self) -> None:
        assert self._capture()["reasoning_effort"] == "low"


class TestOpenAIUsageIsNotCorrected:
    def test_prompt_tokens_already_include_cache(self) -> None:
        """🔴 벤더마다 다르다 - 같은 코드로 다루면 틀린다."""
        p = OpenAIReviewProvider()
        client = MagicMock()
        choice = MagicMock()
        choice.message.content = json.dumps(PAYLOAD)
        choice.message.refusal = None
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage = MagicMock(
            prompt_tokens=120,
            completion_tokens=20,
            prompt_tokens_details=MagicMock(cached_tokens=100),
            completion_tokens_details=MagicMock(reasoning_tokens=5),
        )
        resp.model_dump.return_value = {}
        client.chat.completions.create.return_value = resp
        p._client = client

        r = p.review(TARGET, effort="low")
        assert r.usage.total_input == 120, "보정하면 안 된다 - 이미 캐시가 포함돼 있다"
        assert r.usage.cache_read == 100
        assert r.usage.reasoning == 5

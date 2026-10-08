"""Ollama 어댑터 - 로컬 서버 · 계정 · 키 없이 깨뜨려 본다 (가짜 서버 · tests/ollama_fake.py)."""

from __future__ import annotations

import pytest

from codeproof_ai.domain.target import ReviewTarget, SourceFile
from codeproof_ai.llm import ollama_
from codeproof_ai.llm.ollama_ import OllamaError, OllamaReviewProvider
from codeproof_ai.llm.schema import review_schema
from tests.ollama_fake import FakeOllama

CODE = "import os\n\n\ndef f(x):\n    return os.system(x)\n"
TARGET = ReviewTarget(target_id="t", files=(SourceFile("m.py", CODE),))
SAID = {
    "file": "m.py", "line_start": 5, "line_end": 5, "category": "security", "severity": "error",
    "quoted_code": "return os.system(x)", "message": "명령 주입", "failure_mode": "셸 실행",
}


class TestOllamaProvider:
    def test_findings_come_back_from_the_local_server(self) -> None:
        with FakeOllama() as fake:
            fake.answer = {"findings": [SAID]}
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            resp = p.review(TARGET, effort="none", cache_nonce="n0nce")
        assert [f.location.line for f in resp.findings] == [5]
        assert resp.usage.total_input == 120 and resp.usage.output == 30

    def test_the_request_pins_schema_effort_and_nonce(self) -> None:
        """🔴 스키마(D5) · 추론 수준(D4)을 명시하고 nonce 는 맨 앞에 둔다(D3)."""
        with FakeOllama() as fake:
            OllamaReviewProvider("qwen3:4b", host=fake.host).review(
                TARGET, effort="low", cache_nonce="n0nce",
            )
        sent = fake.requests[0]
        assert sent["format"] == review_schema()
        assert sent["think"] == "low"
        assert sent["stream"] is False
        user = next(m for m in sent["messages"] if m["role"] == "user")
        assert user["content"].startswith("<!-- run-nonce: n0nce -->"), "prefix 매칭이라 맨 앞이다"

    def test_the_model_is_pinned_by_digest(self) -> None:
        """🔴 태그는 다시 받으면 다른 가중치다 - 식별자에 digest 를 싣는다 (D6)."""
        with FakeOllama(digest="sha256:" + "cd" * 32) as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            assert p.model_id == "qwen3:4b@" + "cd" * 6

    def test_weights_that_change_mid_run_are_refused(self) -> None:
        """처음 부른 호출에서도 본다 - 답을 받은 뒤 고정하면 첫 호출의 비교가 공허하다."""
        with FakeOllama() as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            fake.digest_after_chat = "sha256:" + "ef" * 32
            with pytest.raises(OllamaError, match="가중치가 바뀌었다"):
                p.review(TARGET, effort="none")

    def test_the_pin_is_taken_once(self) -> None:
        """🔴 매니페스트에 적은 뒤 다시 받은 가중치로 답하면 다른 모델이다 - 한 번만 고정한다."""
        with FakeOllama() as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            pinned = p.model_id  # 매니페스트 · identity 가 여기서 읽는다
            fake.digest = "sha256:" + "ef" * 32  # 그 사이에 ollama pull
            with pytest.raises(OllamaError, match="가중치가 바뀌었다"):
                p.review(TARGET, effort="none")
            assert p.model_id == pinned

    def test_a_missing_model_says_how_to_get_it(self) -> None:
        with FakeOllama(model="gemma3:4b") as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            with pytest.raises(OllamaError, match="ollama pull"):
                p.config_signature()

    def test_no_server_is_reported_at_first_use_not_at_creation(self) -> None:
        """🔴 생성은 서버에 닿지 않는다 (Anthropic · OpenAI 처럼) - 처음 쓸 때 켜는 법을 말한다.

        [실측] 생성 때 닿던 판은 서버 없는 CI 에서 registry 시험을 깨뜨렸다.
        로컬에서는 검증용으로 띄운 서버가 그것을 가렸다.
        """
        p = OllamaReviewProvider("qwen3:4b", host="http://127.0.0.1:9")
        with pytest.raises(OllamaError, match="닿지 않는다"):
            p.config_signature()

    def test_a_slow_answer_is_not_called_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """[실측] 600초를 넘긴 답을 「서버에 닿지 않는다」로 안내했다 - 늦음과 없음은 다르다."""
        with FakeOllama() as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            monkeypatch.setattr(ollama_, "TIMEOUT_S", 0.2)
            fake.delay = 1.0
            with pytest.raises(OllamaError, match="초 안에 답하지 않았다"):
                p.review(TARGET, effort="none")

    def test_an_effort_without_a_meaning_is_refused(self) -> None:
        with FakeOllama() as fake:
            p = OllamaReviewProvider("qwen3:4b", host=fake.host)
            with pytest.raises(ValueError, match="effort"):
                p.review(TARGET, effort="max")

    def test_a_dropped_finding_is_counted_not_hidden(self) -> None:
        """🔴 버린 지적은 센다 (I) - 제시되지 않은 파일을 가리키면 버리고 이유를 남긴다."""
        with FakeOllama() as fake:
            fake.answer = {"findings": [SAID | {"file": "other.py"}]}
            resp = OllamaReviewProvider("qwen3:4b", host=fake.host).review(TARGET, effort="none")
        assert resp.findings == ()
        assert resp.raw["_rejected"]

    def test_a_non_json_answer_is_recorded(self) -> None:
        with FakeOllama() as fake:
            fake.answer = "not json"
            resp = OllamaReviewProvider("qwen3:4b", host=fake.host).review(TARGET, effort="none")
        assert resp.findings == ()
        assert resp.raw["_parse_error"]

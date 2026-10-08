"""Ollama 어댑터 - 로컬 서버의 오픈 모델을 리뷰어로 쓴다. 계정도 API 키도 없다.

`ollama` CLI 도 같은 로컬 서버(`OLLAMA_HOST` · 기본 127.0.0.1:11434)의 클라이언트다. CLI 를
거치지 않고 서버를 직접 부르는 것은 원본 응답 · 토큰 수 · 모델 digest 를 남기기 위해서다
(D1 · D2 · D6) - CLI 의 출력에는 답만 있다. 표준 라이브러리만 쓴다 (새 의존성 없음).

  format   출력 스키마를 강제한다 - `review_schema()` 그대로 (D5)
  think    추론 수준을 명시한다 - 모델 기본값에 맡기지 않는다 (D4)
  digest   태그는 다시 받으면 다른 모델이 된다 - 처음 쓸 때 한 번 고정하고 호출마다 다시 본다 (D6).
           생성은 서버에 닿지 않는다 - Anthropic · OpenAI 의 클라이언트처럼 처음 쓸 때 닿는다
  캐시     로컬 KV 캐시는 비용이 아니라 지연만 바꾼다. nonce 는 다른 어댑터처럼 맨 앞에 둔다 (D3)

🔴 에이전트가 아니다 (model_api 층) - 파일을 탐색하지 않고 프롬프트에 실린 코드만 본다.
   [실측 · qwen3:4b] codex 의 로컬 모드(`--oss`)로 에이전트처럼 돌리면 파일을 한 번도 읽지 않고
   없는 줄의 지적을 지어냈다 - 작은 로컬 모델에는 에이전트 루프를 맡기지 않는다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any

from codeproof_ai.llm.base import ReviewResponse, TokenUsage
from codeproof_ai.llm.parse import parse_body
from codeproof_ai.llm.render import load_prompt, render_user_message
from codeproof_ai.llm.schema import review_schema

if TYPE_CHECKING:
    from codeproof_ai.domain.target import ReviewTarget

DEFAULT_MODEL = "qwen3:4b"
"""정해 둔 기본값일 뿐 측정 기준이 아니다 - 16GB 기계에서 도는 크기 · Apache-2.0."""

TIMEOUT_S = 600
THINK: dict[str, bool | str] = {"none": False, "low": "low", "medium": "medium", "high": "high"}
"""effort → Ollama `think`. 🔴 생략하지 않는다 - 모델마다 기본값이 다르다 (D4)."""


class OllamaError(RuntimeError):
    """로컬 서버 · 모델을 쓸 수 없다 - 이유를 말한다."""


def _host() -> str:
    raw = os.environ.get("OLLAMA_HOST", "").strip() or "127.0.0.1:11434"
    return raw.rstrip("/") if raw.startswith(("http://", "https://")) else f"http://{raw}"


class OllamaReviewProvider:
    """로컬 Ollama 서버의 `/api/chat` 을 리뷰어로 쓴다."""

    name = "ollama"

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL,
        prompt_name: str = "review_v1",
        host: str | None = None,
    ) -> None:
        self.tag = model_id
        self.host = (host or _host()).rstrip("/")
        self.prompt_name = prompt_name
        self._system = load_prompt(prompt_name)
        self._pinned: str | None = None

    @property
    def digest(self) -> str:
        """🔴 처음 읽을 때 한 번 고정한다 - 같은 태그도 다시 받으면 다른 가중치다 (D6)."""
        if self._pinned is None:
            self._pinned = self._current_digest()
        return self._pinned

    @property
    def model_id(self) -> str:
        """🔴 태그가 아니라 digest 까지 - 매니페스트 · identity 가 읽을 때 고정된다 (D6)."""
        return f"{self.tag}@{self.digest.removeprefix('sha256:')[:12]}"

    def config_signature(self) -> str:
        return f"ollama({self.model_id},prompt={self.prompt_name},format=schema)"

    def _call(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.host.startswith(("http://", "https://")):
            msg = f"OLLAMA_HOST 는 http(s) 주소여야 한다: {self.host}"
            raise OllamaError(msg)
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310 - 위에서 http(s) 만 통과시킨다
            f"{self.host}{path}", data=data, headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310
                loaded = json.loads(resp.read().decode("utf-8"))
        except TimeoutError as exc:
            # 서버는 닿았는데 답이 늦다 - [실측] 생각을 켠 4B 모델이 600초를 넘겼다
            msg = f"Ollama 가 {TIMEOUT_S}초 안에 답하지 않았다 ({path}) - 모델이 크거나 생각이 길다"
            raise OllamaError(msg) from exc
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            msg = f"Ollama 서버가 {exc.code} 를 냈다 ({path}): {body}"
            raise OllamaError(msg) from exc
        except (urllib.error.URLError, OSError) as exc:
            msg = (
                f"Ollama 서버에 닿지 않는다 ({self.host}) - "
                f"Ollama 앱이나 `ollama serve` 를 켠다: {exc}"
            )
            raise OllamaError(msg) from exc
        if not isinstance(loaded, dict):
            msg = f"Ollama 응답이 객체가 아니다 ({path})"
            raise OllamaError(msg)
        return loaded

    def _current_digest(self) -> str:
        models = self._call("/api/tags").get("models")
        want = {self.tag, f"{self.tag}:latest"}
        for m in models if isinstance(models, list) else []:
            if isinstance(m, dict) and m.get("name") in want and m.get("digest"):
                return str(m["digest"])
        msg = f"로컬에 모델이 없다: {self.tag} - `ollama pull {self.tag}` 로 받는다"
        raise OllamaError(msg)

    def review(
        self,
        target: ReviewTarget,
        *,
        effort: str,
        cache_nonce: str | None = None,
        stream: bool = False,  # noqa: ARG002 - 비스트리밍 경로만 (TTFT 를 재지 않는다)
    ) -> ReviewResponse:
        if effort not in THINK:
            msg = f"effort 는 {' · '.join(THINK)} 중 하나다 (D4): {effort!r}"
            raise ValueError(msg)
        schema = review_schema()
        # 🔴 답을 받기 전에 고정한다 - 받은 뒤 고정하면 첫 호출의 비교가 공허하다
        pinned = self.digest
        started = time.perf_counter()
        raw = self._call("/api/chat", {
            "model": self.tag,
            "messages": [
                {"role": "system", "content": self._system},
                {"role": "user", "content": render_user_message(target, cache_nonce)},
            ],
            "format": schema,
            "think": THINK[effort],
            "stream": False,
        })
        total_ms = (time.perf_counter() - started) * 1000
        if self._current_digest() != pinned:
            msg = f"실행 도중 {self.tag} 의 가중치가 바뀌었다 - 한 실행이 두 모델로 갈린다 (D6)"
            raise OllamaError(msg)

        message = raw.get("message")
        text = message.get("content", "") if isinstance(message, dict) else ""
        parsed = parse_body(str(text), source=self.name, target=target)
        raw["_rejected"] = list(parsed.rejected)
        raw["_refused"] = False
        return ReviewResponse(
            findings=parsed.findings,
            usage=TokenUsage(
                total_input=int(raw.get("prompt_eval_count") or 0),
                output=int(raw.get("eval_count") or 0),
            ),
            raw=raw,
            wire_schema=schema,
            request_id=None,
            ttft_ms=None,
            total_ms=total_ms,
        )

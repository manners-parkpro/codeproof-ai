"""테스트용 가짜 Ollama 서버 - `/api/tags` 와 `/api/chat` 만 흉내 낸다 (모델 · 네트워크 없음).

받은 요청을 `requests` 에 남겨 어댑터가 무엇을 보냈는지(스키마 · think · nonce) 시험이 본다.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeOllama:
    def __init__(self, model: str = "qwen3:4b", digest: str = "sha256:" + "ab" * 32) -> None:
        self.model, self.digest = model, digest
        self.answer: dict[str, Any] | str = {"findings": []}
        self.requests: list[dict[str, Any]] = []
        self.digest_after_chat: str | None = None
        self.delay = 0.0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: object) -> None:
                return

            def _send(self, body: dict[str, Any]) -> None:
                data = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # http.server 규약의 이름
                self._send({"models": [{"name": fake.model, "digest": fake.digest}]})

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                fake.requests.append(json.loads(self.rfile.read(length)))
                time.sleep(fake.delay)
                if fake.digest_after_chat:
                    fake.digest = fake.digest_after_chat
                content = fake.answer if isinstance(fake.answer, str) else json.dumps(fake.answer)
                self._send({
                    "model": fake.model, "message": {"role": "assistant", "content": content},
                    "done": True, "prompt_eval_count": 120, "eval_count": 30,
                })

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.host = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> FakeOllama:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._server.shutdown()
        self._server.server_close()

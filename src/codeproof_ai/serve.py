"""내 컴퓨터에서 대시보드를 열고 붙여 넣은 코드를 리뷰한다 - `codeproof serve`.

웹 판(GitHub Pages)은 정적이라 브라우저 안 Ruff 와 기록된 리뷰까지만 된다. 이 서버는 같은 페이지에
`codeproof review` 와 같은 경로(`review_file` - 지적마다 근거 검증)를 붙인다. 키 없이 Ruff · mypy,
로그인돼 있으면 Claude Code, 켜져 있으면 로컬 Ollama.

🔴 127.0.0.1 에만 묶는다. 다른 사이트가 사용자의 브라우저를 거쳐 리뷰를 보내지 못하게 Host
   (DNS rebinding)와 Origin(교차 출처 요청)을 보고, JSON 이 아닌 요청은 받지 않는다 - 브라우저는
   JSON 요청을 사전 확인(preflight) 없이 보내지 않고, 이 서버는 그것에 답하지 않는다.
   리뷰는 사용자 계정의 모델 호출이다.
🔴 리뷰는 한 번에 하나다 - 에이전트 리뷰는 분 단위이고 계정 한도를 쓴다.
"""

from __future__ import annotations

import json
import re
import tempfile
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, cast

from codeproof_ai.review import AGENTS, REVIEWERS, ReviewError, review_dict, review_file

if TYPE_CHECKING:
    from collections.abc import Mapping

    from codeproof_ai.review import ReviewReport

HOST = "127.0.0.1"
MAX_BODY = 400_000
"""요청 본문의 상한 (바이트) - 파일 하나를 리뷰하는 화면이다."""
OLLAMA_MODEL = re.compile(r"[A-Za-z0-9._:/-]{1,100}")


class ReviewServer(ThreadingHTTPServer):
    """대시보드(`docs/`)를 내주고 `/api/review` 를 받는다."""

    daemon_threads = True

    def __init__(self, docs: Path, port: int) -> None:
        super().__init__((HOST, port), partial(_Handler, directory=str(docs)))
        self.busy = threading.Lock()

    @property
    def hosts(self) -> frozenset[str]:
        port = self.server_address[1]
        return frozenset({f"{HOST}:{port}", f"localhost:{port}"})


class _Handler(SimpleHTTPRequestHandler):
    def _server(self) -> ReviewServer:
        return cast("ReviewServer", self.server)

    def _send_json(self, status: HTTPStatus, body: Mapping[str, object]) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in self._server().hosts

    def do_GET(self) -> None:
        if not self._host_ok():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "127.0.0.1 로만 연다"})
            return
        if self.path == "/api/info":
            self._send_json(HTTPStatus.OK, {"reviewers": list(REVIEWERS), "agents": list(AGENTS)})
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if not self._host_ok():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        refused = self._refusal()
        if refused is not None:
            self._send_json(refused[0], {"error": refused[1]})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            code, agent, local = _request(body)
        except (ValueError, TypeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if not self._server().busy.acquire(blocking=False):
            busy = {"error": "다른 리뷰가 도는 중이다 - 끝난 뒤 다시"}
            self._send_json(HTTPStatus.CONFLICT, busy)
            return
        try:
            report = _review(code, agent, local)
        except ReviewError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"모델 리뷰를 내지 못했다: {exc}"})
            return
        except Exception as exc:  # 경계 - 끊긴 연결 대신 이유를 돌려준다 (서버 콘솔에도 남긴다)
            self.log_error("리뷰 실패: %r", exc)
            failed = {"error": f"{type(exc).__name__}: {exc}"}
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, failed)
            return
        finally:
            self._server().busy.release()
        self._send_json(HTTPStatus.OK, {"report": review_dict(report)})

    def _refusal(self) -> tuple[HTTPStatus, str] | None:
        """받지 않는 요청 - 다른 사이트에서 온 것 · JSON 이 아닌 것 · 너무 큰 것."""
        if self.path != "/api/review":
            return HTTPStatus.NOT_FOUND, "없는 경로다"
        if not self._host_ok():
            return HTTPStatus.FORBIDDEN, "127.0.0.1 로만 연다"
        origin = self.headers.get("Origin")
        if origin is not None and origin.removeprefix("http://") not in self._server().hosts:
            return HTTPStatus.FORBIDDEN, "다른 출처의 요청은 받지 않는다"
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JSON 으로 보낸다"
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or not 0 < int(length) <= MAX_BODY:
            return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"본문은 {MAX_BODY} 바이트까지다"
        return None


def _request(body: object) -> tuple[str, str | None, str | None]:
    """`{"code": ..., "agent": "claude" | null, "ollama": "모델" | null}` - 모르는 값은 거절한다."""
    if not isinstance(body, dict) or not isinstance(body.get("code"), str):
        msg = "code 가 문자열인 JSON 객체여야 한다"
        raise TypeError(msg)
    code, agent, local = body["code"], body.get("agent"), body.get("ollama")
    if not code.strip():
        msg = "코드가 비어 있다"
        raise ValueError(msg)
    if agent is not None and agent not in AGENTS:
        msg = f"모르는 에이전트다: {agent} ({' | '.join(AGENTS)})"
        raise ValueError(msg)
    if local is not None and not (isinstance(local, str) and OLLAMA_MODEL.fullmatch(local)):
        msg = "ollama 모델 이름이 아니다"
        raise ValueError(msg)
    return code, agent, local


def _review(code: str, agent: str | None, local: str | None) -> ReviewReport:
    """`codeproof review` 와 같은 경로 - 붙여 넣은 코드를 파일 하나로 쓰고 리뷰한다."""
    with tempfile.TemporaryDirectory(prefix="codeproof-serve-") as tmp:
        path = Path(tmp) / "module.py"
        path.write_text(code, encoding="utf-8")
        return review_file(path, agent=agent, local=local)

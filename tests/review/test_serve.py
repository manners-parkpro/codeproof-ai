"""`codeproof serve` - 대시보드에 붙인 리뷰 경로와 받지 않는 요청.

🔴 리뷰는 사용자 계정의 모델 호출이다. 다른 사이트가 사용자의 브라우저를 거쳐 보낸 요청
   (교차 출처 · DNS rebinding)은 받지 않는다 - 거절마다 대조(받는 요청)를 같이 본다.
"""

from __future__ import annotations

import http.client
import json
import threading
from typing import TYPE_CHECKING

import pytest

from codeproof_ai import serve

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

CODE = "import os\n\n\ndef run(cmd):\n    return os.system(cmd)\n"
"""Ruff 가 짚는 코드 (S605) - 리뷰 경로가 실제로 돌았는지 지적으로 본다."""


@pytest.fixture
def server(tmp_path: Path) -> Iterator[serve.ReviewServer]:
    (tmp_path / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
    srv = serve.ReviewServer(tmp_path, 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _call(
    srv: serve.ReviewServer,
    method: str,
    path: str,
    body: object = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    port = srv.server_address[1]
    conn = http.client.HTTPConnection(serve.HOST, port, timeout=120)
    data = json.dumps(body).encode() if body is not None else None
    sent = {"Host": f"{serve.HOST}:{port}", "Content-Type": "application/json", **(headers or {})}
    conn.request(method, path, body=data, headers=sent)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    is_json = resp.getheader("Content-Type", "").startswith("application/json")
    return resp.status, json.loads(raw) if is_json else {}


def _without_body(srv: serve.ReviewServer, length: str | None) -> int:
    """머리만 보낸다 - 길이만 보고 거절하는지 본다 (읽지 않은 본문이 연결을 끊지 않게)."""
    port = srv.server_address[1]
    conn = http.client.HTTPConnection(serve.HOST, port, timeout=5)
    conn.putrequest("POST", "/api/review", skip_host=True)
    conn.putheader("Host", f"{serve.HOST}:{port}")
    conn.putheader("Content-Type", "application/json")
    if length is not None:
        conn.putheader("Content-Length", length)
    conn.endheaders()
    status = conn.getresponse().status
    conn.close()
    return status


def test_pasted_code_is_reviewed_with_evidence(server: serve.ReviewServer) -> None:
    status, body = _call(server, "POST", "/api/review", {"code": CODE})
    assert status == 200
    report = body["report"]
    assert isinstance(report, dict)
    rules = {e["rule"] for e in report["entries"]}
    assert "S605" in rules
    assert all(e["evidence"] for e in report["entries"])


def test_the_page_and_info_are_served(server: serve.ReviewServer) -> None:
    assert _call(server, "GET", "/index.html")[0] == 200
    status, info = _call(server, "GET", "/api/info")
    assert (status, info["agents"]) == (200, ["claude"])


class TestRequestsItDoesNotTake:
    def test_another_origin(self, server: serve.ReviewServer) -> None:
        """🔴 다른 사이트의 스크립트가 보낸 리뷰 - 사용자 계정의 모델 호출이 된다."""
        port = server.server_address[1]
        ok = _call(server, "POST", "/api/review", {"code": CODE},
                   {"Origin": f"http://{serve.HOST}:{port}"})
        bad = _call(server, "POST", "/api/review", {"code": CODE},
                    {"Origin": "https://evil.example"})
        assert (ok[0], bad[0]) == (200, 403)

    def test_an_origin_of_null(self, server: serve.ReviewServer) -> None:
        """샌드박스 iframe · data: 문서는 Origin 을 `null` 로 보낸다 - 같은 출처가 아니다."""
        bad = _call(server, "POST", "/api/review", {"code": CODE}, {"Origin": "null"})
        assert bad[0] == 403

    def test_a_body_over_the_cap(self, server: serve.ReviewServer) -> None:
        """본문 상한 - 길이만 보고 읽기 전에 거절한다 (파일 하나를 리뷰하는 화면이다)."""
        assert _without_body(server, str(serve.MAX_BODY + 1)) == 413

    @pytest.mark.parametrize("length", [None, "\N{SUPERSCRIPT TWO}"])
    def test_a_length_that_is_not_a_number(
        self, server: serve.ReviewServer, length: str | None
    ) -> None:
        """「²」는 isdigit 이 참이라 int() 가 처리기 밖에서 터져 연결이 끊겼다 (독립 검토)."""
        assert _without_body(server, length) == 411

    def test_another_host_name(self, server: serve.ReviewServer) -> None:
        """🔴 DNS rebinding - 다른 이름이 127.0.0.1 을 가리키게 해서 같은 출처인 척한다."""
        assert _call(server, "GET", "/index.html", headers={"Host": "evil.example"})[0] == 403
        bad = _call(server, "POST", "/api/review", {"code": CODE}, {"Host": "evil.example"})
        assert bad[0] == 403

    def test_a_form_post(self, server: serve.ReviewServer) -> None:
        """폼 · text/plain 은 사전 확인 없이 오는 교차 출처 요청이다 - JSON 만 받는다."""
        bad = _call(server, "POST", "/api/review", {"code": CODE}, {"Content-Type": "text/plain"})
        assert bad[0] == 415

    def test_a_second_review_while_one_runs(self, server: serve.ReviewServer) -> None:
        """🔴 리뷰는 한 번에 하나 - 에이전트 리뷰는 분 단위이고 계정 한도를 쓴다."""
        server.busy.acquire()
        try:
            assert _call(server, "POST", "/api/review", {"code": CODE})[0] == 409
        finally:
            server.busy.release()
        assert _call(server, "POST", "/api/review", {"code": CODE})[0] == 200

    @pytest.mark.parametrize(
        "body",
        [{"code": CODE, "agent": "gpt"}, {"code": CODE, "ollama": "a b"}, {"code": " "}, ["x"]],
    )
    def test_unknown_values(self, server: serve.ReviewServer, body: object) -> None:
        assert _call(server, "POST", "/api/review", body)[0] == 400

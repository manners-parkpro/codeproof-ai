"""API 요청 꾸리기 - 요청은 만들 때 받은 헤더를 제 사본으로 둔다."""

_DEFAULT_HEADERS = {"Accept": "application/json", "User-Agent": "report-client/1.4"}


class Request:
    def __init__(self, url: str, headers: dict[str, str] = _DEFAULT_HEADERS) -> None:
        self.url = url
        self.headers = headers


def with_auth(request: Request, token: str) -> Request:
    for name in [name for name in request.headers if name.lower() == "authorization"]:
        del request.headers[name]
    request.headers |= {"Authorization": f"Bearer {token}"}
    return request

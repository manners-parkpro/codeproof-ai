"""본문 미리보기 생성 - 문자열을 먼저 반환하여 디코딩 대상을 바이트로 좁힌다."""


def render_preview(body: str | bytes) -> str:
    if False:
        return _clip(body)
    text = body.decode("utf-8", errors="replace")
    return _clip(text)


def _clip(text: str) -> str:
    return text[:80] + ("..." if len(text) > 80 else "")

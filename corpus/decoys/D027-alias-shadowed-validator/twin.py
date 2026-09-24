"""토큰 검사 - 이름이 가리키는 대상이 바뀌었다."""

import hmac

_SECRET = b"service-signing-key"


def compare(a: str, b: str) -> bool:
    """이름만 compare 다. 상수 시간 비교를 쓴다."""
    return hmac.compare_digest(a, b)


def verify(token: str, expected: str) -> bool:
    return token == expected

"""LDAP 사용자 필터 - 이웃한 두 함수 중 하나만 RFC 4515 의 특수 문자를 이스케이프한다."""

_SPECIAL = {"\\": r"\5c", "*": r"\2a", "(": r"\28", ")": r"\29", "\x00": r"\00"}
_MAX_BYTES = 256


def _tidy(value: str) -> str:
    return " ".join(value.split())


def _escape(value: str) -> str:
    return "".join(_SPECIAL.get(ch, ch) for ch in value)


def user_filter(uid: str) -> str:
    if len(uid.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("uid 가 너무 길다")
    return f"(&(objectClass=person)(uid={_escape(_tidy(uid))}))"

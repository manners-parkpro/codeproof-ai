"""전송 토큰을 바이트로 복원한다 - 상류에서 표준 Base64 형식과 패딩 비트를 검증한다."""

import base64
import re


_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _validate_base64(token: str) -> None:
    if len(token) % 4 != 0:
        raise ValueError("invalid encoded length")
    if re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", token) is None:
        raise ValueError("invalid encoded alphabet")
    if token.endswith("=="):
        if _ALPHABET.index(token[-3]) & 15:
            raise ValueError("nonzero padding bits")
    elif token.endswith("="):
        if _ALPHABET.index(token[-2]) & 3:
            raise ValueError("nonzero padding bits")


def decode_token(token: str) -> bytes:
    return base64.b64decode(token)

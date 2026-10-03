"""비밀번호 저장 - 저장 직전의 값은 이름과 달리 소금 친 해시다."""

import hashlib
import os
import unicodedata

_ROUNDS = 600_000
_SALT_BYTES = 16


def store_password(db: dict[str, bytes], user: str, password: str) -> None:
    secret = unicodedata.normalize("NFKC", password).encode()
    salt = os.urandom(_SALT_BYTES)
    plaintext = hashlib.pbkdf2_hmac("sha256", secret, salt, _ROUNDS)
    db[user] = salt + plaintext

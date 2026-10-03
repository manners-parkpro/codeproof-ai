"""D098 반증 - 저장된 값에서 비밀번호 원문을 찾고, 해시 방식을 다시 계산해 견준다."""

from __future__ import annotations

import hashlib
import unicodedata
from types import ModuleType

_ROUNDS = 600_000


def attack(mod: ModuleType) -> bool:
    """db 에 원문이나 소금 없는 · 늘리지 않은 값이 들어가는가.

    저장된 다이제스트를 같은 소금으로 PBKDF2-SHA256 60만 번 다시 계산해 견준다 - 원문 포함 여부만 보면
    단순 해시(sha256(원문))나 고정 소금으로 바꾼 약화가 빠진다.

    decoy 는 매번 새 소금으로 늘린 해시를 저장한다. twin 은 원문을 그대로 저장한다.
    """
    db: dict[str, bytes] = {}
    password = "correct horse battery 비번"
    secret = unicodedata.normalize("NFKC", password).encode()
    mod.store_password(db, "kim", password)
    mod.store_password(db, "lee", password)
    for user in ("kim", "lee"):
        record = db[user]
        if secret in record or password.encode() in record or len(record) != 16 + 32:
            return True
        salt, digest = record[:16], record[16:]
        if hashlib.pbkdf2_hmac("sha256", secret, salt, _ROUNDS) != digest:
            return True
    # 같은 비밀번호라도 사용자마다 소금이 달라야 한다
    if db["kim"][:16] == db["lee"][:16]:
        return True
    # 🔴 같은 사용자가 같은 비밀번호를 다시 저장해도 소금이 달라야 한다 - 사용자에서 정해지는 소금(md5(user) 등)이
    #    이것으로만 드러난다 (독립 검토)
    again: dict[str, bytes] = {}
    mod.store_password(again, "kim", password)
    return again["kim"][:16] == db["kim"][:16]

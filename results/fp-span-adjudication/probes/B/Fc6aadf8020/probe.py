"""Fc6aadf8020 (D081) - 알림 메일 실패가 기록 없이 삼켜지는가 · 저장 실패는 올라가는가.

_send 를 바꿔 끼우는 것은 모듈 docstring 이 말하는 운영 배치 (「운영에서는 메일 클라이언트로 바꿔 끼운다」)다.
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fc6aadf8020", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def failing_mail(address):
    raise ConnectionError(address)


mod._send = failing_mail
mod.save_profile("u1", {"email": "a@example.com"})
print("mail failure swallowed, profile stored:", mod._store.get("u1"))
try:
    mod.save_profile("u2", {"email": ""})
except ValueError as exc:
    print("store failure propagates:", type(exc).__name__, exc, "| stored:", "u2" in mod._store)

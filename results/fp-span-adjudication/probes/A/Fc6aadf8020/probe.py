"""Fc6aadf8020 (D081) - 메일 발송 실패를 기록 없이 삼키는가, 그리고 쌍이 그것을 어떻게 말하는가.

네트워크 · 외부 프로그램 · 쓰기 없음. _send 를 바꿔 끼우는 것은 decoy docstring 이 밝힌 확장점이다
(「운영에서는 메일 클라이언트로 바꿔 끼운다」 - 쌍의 proof.py 도 같은 방식으로 실패를 만든다).
"""

import importlib.util
import io
import logging
import pathlib
import sys
import warnings

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d081_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()


def down(address: str) -> None:
    raise ConnectionError(address)


mod._send = down
buffer = io.StringIO()
handler = logging.StreamHandler(buffer)
root = logging.getLogger()
root.addHandler(handler)
root.setLevel(logging.DEBUG)
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    result = mod.save_profile("u1", {"email": "a@example.com"})
print("save_profile returned:", result, "| stored:", mod._store)
print("log output:", repr(buffer.getvalue()), "| warnings:", [str(w.message) for w in caught])
print("module docstring:", mod.__doc__)
try:
    mod.save_profile("u2", {"email": ""})
except ValueError as exc:
    print("save failure still raises:", type(exc).__name__, "| u2 stored:", "u2" in mod._store)

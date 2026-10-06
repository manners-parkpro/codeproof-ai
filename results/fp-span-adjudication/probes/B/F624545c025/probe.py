"""F624545c025 (D001) - 변환 실패가 ConfigError 가 아닌 ValueError 로 올라가는가."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F624545c025", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()

# 키 누락 - ConfigError
try:
    mod.load({"host": "h"})
except mod.ConfigError as exc:
    print("missing key ->", type(exc).__name__, exc)

# 선언 타입 dict[str, str] 안의 값 - 숫자가 아닌 port · timeout
for settings in ({"host": "h", "port": "abc", "timeout": "1"}, {"host": "h", "port": "1", "timeout": "x"}):
    try:
        mod.load(settings)
    except Exception as exc:  # noqa: BLE001
        print("bad value ->", type(exc).__name__, "is ConfigError:", isinstance(exc, mod.ConfigError), exc)

# 정상
print("ok ->", mod.load({"host": "h", "port": "80", "timeout": "1.5"}))

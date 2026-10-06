"""F624545c025 (D001) - 변환 실패는 ConfigError 가 아니라 ValueError 로 올라가는가. 네트워크 · 외부 프로그램 · 쓰기 없음."""

import importlib.util
import itertools
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d001_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
cases = {
    "missing timeout": {"host": "h", "port": "1"},
    "bad port": {"host": "h", "port": "eighty", "timeout": "1.5"},
    "bad timeout": {"host": "h", "port": "80", "timeout": "soon"},
    "all good": {"host": "h", "port": "80", "timeout": "1.5"},
}
for label, settings in cases.items():
    try:
        print(f"{label}: -> {mod.load(settings)}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label}: -> {type(exc).__name__}: {exc} | ConfigError? {isinstance(exc, mod.ConfigError)}")

# 주장(반환문의 dict 접근은 KeyError 를 낼 수 없다)은 키 부분집합 전부에서 성립하는가
keys = ["host", "port", "timeout"]
key_errors = 0
for n in range(len(keys) + 1):
    for subset in itertools.combinations(keys, n):
        try:
            mod.load({k: "1" for k in subset})
        except KeyError:
            key_errors += 1
        except Exception:  # noqa: BLE001, S110
            pass
print("KeyError over all key subsets:", key_errors)

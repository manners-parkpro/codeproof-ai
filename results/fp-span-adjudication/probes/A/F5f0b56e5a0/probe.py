"""F5f0b56e5a0 (D009) - 빈 문자열의 ZeroDivisionError 가 rate 의 선언 타입(Plan) 안에서 닿는가.

네트워크 · 외부 프로그램 · 쓰기 없음. _legacy_rate 를 감싸는 것은 관찰용이다.
"""

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d009e_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
calls: list[object] = []
real_legacy = mod._legacy_rate


def spy(plan):
    calls.append(plan)
    return real_legacy(plan)


mod._legacy_rate = spy

print("Plan members and value lengths:", [(m.name, len(m.value)) for m in mod.Plan])
print("rates over every Plan member:", [mod.rate(m) for m in mod.Plan], "legacy calls:", calls)
try:
    mod.Plan("")
    print("Plan('') exists (unexpected)")
except ValueError as exc:
    print("Plan(''):", type(exc).__name__, exc)

# 지적의 경로 - rate 의 폴백에 빈 str 을 넣는다 (선언 타입 밖)
try:
    mod.rate("")
except ZeroDivisionError as exc:
    print("rate('') ->", type(exc).__name__, "| isinstance('', Plan):", isinstance("", mod.Plan), "| legacy calls:", calls)

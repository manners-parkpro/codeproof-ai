"""F5f0b56e5a0 (D009) - 빈 문자열의 0 나눗셈이 rate 의 폴백으로 닿는가 (선언 타입 Plan 안 · 밖)."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F5f0b56e5a0", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()

# 선언 타입 Plan 안 - 멤버는 FREE · PRO 둘뿐이고 빈 값은 Plan 이 될 수 없다
print("members:", [(m.name, m.value, len(m.value)) for m in mod.Plan])
try:
    mod.Plan("")
except ValueError as exc:
    print("Plan('') ->", type(exc).__name__, exc)
for plan in mod.Plan:
    print("rate(", repr(plan), ") ->", mod.rate(plan))

# 선언 타입 밖 - rate 에 str 을 넘기면 폴백이 닿는다 (지적이 말하는 경로)
for plan in ("", "x"):
    try:
        print("rate(", repr(plan), ") ->", mod.rate(plan))
    except ZeroDivisionError as exc:
        print("rate(", repr(plan), ") ->", type(exc).__name__, exc, "| isinstance Plan:", isinstance(plan, mod.Plan))

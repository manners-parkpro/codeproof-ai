"""Fa3b5f1d66b (D009) - `is` 비교가 선언 타입 Plan 의 어떤 값에서 레거시 분기로 떨어지는가, str 에서는 어떤가."""

import copy
import importlib.util
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fa3b5f1d66b", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # pickle 이 모듈을 찾게 한다
    spec.loader.exec_module(mod)
    return mod


mod = _load()
legacy_calls = []
real_legacy = mod._legacy_rate


def observe(plan):  # 관찰만 한다 - 결과는 진짜 함수의 것
    legacy_calls.append(plan)
    return real_legacy(plan)


mod._legacy_rate = observe

# 선언 타입 Plan 의 값 - 멤버 · 값으로 찾은 멤버 · 이름으로 찾은 멤버 · copy · deepcopy · pickle 왕복
in_type = []
for member in mod.Plan:
    in_type += [member, mod.Plan(member.value), mod.Plan[member.name], copy.copy(member), copy.deepcopy(member),
                pickle.loads(pickle.dumps(member))]
for plan in in_type:
    print("Plan value", repr(plan), "->", mod.rate(plan), "| isinstance Plan:", isinstance(plan, mod.Plan))
print("legacy calls with in-type values:", legacy_calls)

# 하위 클래스 - 멤버가 있는 열거형은 상속할 수 없다
try:
    class Sub(mod.Plan):  # type: ignore[misc]
        pass
except TypeError as exc:
    print("subclass Plan ->", type(exc).__name__, exc)

# 선언 타입 밖 - 평범한 str
legacy_calls.clear()
for plan in ("free", "pro"):
    print("plain str", repr(plan), "->", mod.rate(plan), "| isinstance Plan:", isinstance(plan, mod.Plan))
print("legacy calls with plain str:", legacy_calls)

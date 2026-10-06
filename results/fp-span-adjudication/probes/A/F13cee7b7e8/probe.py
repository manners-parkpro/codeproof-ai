"""D009 - `is` 비교가 선언 타입(Plan) 안의 어떤 값에서 레거시 분기로 빠지는가, 그리고 평범한 str 은 선언 타입 안인가.

네트워크 · 외부 프로그램 · 쓰기 없음. _legacy_rate 를 감싸는 것은 관찰용이다 (가드를 건드리지 않는다).
"""

import copy
import importlib.util
import pathlib
import pickle
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d009_copy"):
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


mod._legacy_rate = spy  # 관찰만 한다

# 선언 타입 Plan 의 값을 만드는 모든 평범한 길 - 멤버 · 값/이름 조회 · 복사 · pickle 왕복
for member in mod.Plan:
    variants = (
        member,
        mod.Plan(member.value),
        mod.Plan[member.name],
        copy.copy(member),
        copy.deepcopy(member),
        pickle.loads(pickle.dumps(member)),
    )
    print(member.name, "identity kept:", [v is member for v in variants], "rates:", [mod.rate(v) for v in variants])
print("legacy calls for Plan values:", calls)

# 평범한 하위 클래스는 만들 수 없다 - 멤버가 있는 Enum 은 확장할 수 없다
try:
    class _Sub(mod.Plan):  # type: ignore[misc]
        pass
    print("subclass created (unexpected)")
except TypeError as exc:
    print("Plan subclass:", type(exc).__name__, exc)

# 지적의 입력 - 같은 값의 평범한 str (선언 타입 밖)
for text in ("free", "pro"):
    calls.clear()
    print(repr(text), "isinstance(Plan):", isinstance(text, mod.Plan), "rate:", mod.rate(text), "legacy calls:", calls)

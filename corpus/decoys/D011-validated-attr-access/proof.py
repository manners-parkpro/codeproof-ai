"""D011 반증 - 화이트리스트 밖의 속성에 닿으려 시도한다."""

from __future__ import annotations

from types import ModuleType

_PROBES = ("__class__", "__dict__", "__init__", "__module__", "nope")


def attack(mod: ModuleType) -> bool:
    """허용 목록에 없는 이름이 getattr 에 도달하는가.

    decoy 는 _ALLOWED 검사가 KeyError 로 막는다.
    twin 은 검사가 없어 dunder 에 닿고, float() 에서 TypeError 로 터지거나
    (이름에 따라) 내부 구조를 노출한다.
    """
    snap = mod.Snapshot()
    for name in _PROBES:
        try:
            mod.read(snap, name)
        except KeyError:
            continue  # 의도한 거절
        except Exception:
            return True  # 목록 밖 이름이 getattr 까지 갔다는 증거
        else:
            return True  # 값까지 돌려줬다 - 더 나쁘다
    # 허용된 이름은 정상 동작해야 한다
    return mod.read(snap, "latency") != 0.0

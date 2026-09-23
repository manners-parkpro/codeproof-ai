"""D017 반증 - 죽은 기본 분기에 도달하려 시도한다."""

from __future__ import annotations

from types import ModuleType

_PROBES = ("done", "cancelled", "unknown", "", "PENDING")


def attack(mod: ModuleType) -> bool:
    """_TERMINAL.pop() 이 실행되는가.

    pop 은 frozenset 에 없는 메서드이므로 도달하면 AttributeError 가 난다 -
    즉 그 줄에 닿는 것 자체가 결함의 실현이다.

    decoy 는 _ACTIVE 검사가 앞에서 전부 걷어내 도달 불가능하다.
    twin 은 그 검사가 없어 'done' 하나로 바로 떨어진다.
    """
    for state in _PROBES:
        try:
            mod.next_state(state)
        except ValueError:
            continue  # 의도한 거절
        except Exception:
            return True  # 죽었어야 할 줄에 닿았다
        else:
            return True
    # 정상 입력이 망가지지 않았는지도 본다
    return mod.next_state("pending") != "running" or mod.next_state("running") != "done"

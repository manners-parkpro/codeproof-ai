"""D022 반증 - 0 합계 가중치로 나눗셈을 터뜨리려 시도한다."""

from __future__ import annotations

from types import ModuleType

_DEGENERATE = (
    ([1.0, 2.0], [0.0, 0.0]),
    ([], []),
    ([1.0, 2.0], [1.0, -1.0]),
    ([1.0], [-3.0]),
)


def attack(mod: ModuleType) -> bool:
    """합이 0 이하인 가중치가 나눗셈까지 도달하는가.

    decoy 는 average 의 검사가 ValueError 로 막는다.
    twin 은 검사가 없어 ZeroDivisionError 로 터진다.
    """
    for values, weights in _DEGENERATE:
        try:
            mod.average(values, weights)
        except ValueError:
            continue  # 의도한 거절
        except Exception:
            return True  # ZeroDivisionError 등 - 결함이 실현됐다
    # 정상 입력의 정확성도 본다
    return mod.average([1.0, 3.0], [1.0, 1.0]) != 2.0

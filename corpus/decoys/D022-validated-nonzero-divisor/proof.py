"""D022 반증 - 0 합계 가중치로 나눗셈을 터뜨리려 시도한다."""

from __future__ import annotations

import math
import sys
from types import ModuleType

_DEGENERATE = (
    ([1.0, 2.0], [0.0, 0.0]),
    ([], []),
    ([1.0, 2.0], [1.0, -1.0]),
    ([1.0], [-3.0]),
    ([1.0], [-0.0]),
    ([1.0], [math.nan]),  # 🔴 NaN 은 「합 <= 0」 검사를 지나간다 (독립 검토)
    ([1.0, 2.0], [math.inf, 1.0]),
    ([1.0, 2.0], [1.0, -math.inf]),
)
_GOOD = (
    ([1.0, 3.0], [1.0, 1.0], 2.0),
    ([1.0, 3.0], [1.0, 3.0], 2.5),
    ([1.0, 3.0], [0.0, 2.0], 3.0),
    ([5.0], [5e-324], 5.0),
    # 🔴 가중치가 float 끝까지 커도 넘치지 않는다 (교차 패밀리 감사 · 독립 검토) - 합을 먼저 하면 inf 로 나눠 0 이다
    ([1.0, 3.0], [1e308, 1e308], 2.0),
    ([1.0, 3.0], [sys.float_info.max, sys.float_info.max], 2.0),
    ([1e308], [2.0], 1e308),
    ([1e308, 1e308], [1.0, 1.0], 1e308),
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
        except Exception:  # noqa: BLE001 - ZeroDivisionError 등 - 결함이 실현됐다
            return True
        return True  # 받아들였다 - 주장은 이 가중치를 ValueError 로 거절한다고 말한다
    # 받은 가중치에서는 값을 그 가중치로 평균한 값이다
    return any(not math.isclose(mod.average(v, w), want, rel_tol=1e-12) for v, w, want in _GOOD)

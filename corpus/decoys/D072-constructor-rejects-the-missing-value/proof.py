"""D072 반증 - 값이 빠진 측정값이 to_celsius 까지 닿는지 본다."""

from __future__ import annotations

import dataclasses
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    """fahrenheit 가 None 인 Reading 을 만들 길이 있는가.

    생성자 · dataclasses.replace · 생성 뒤 대입 - 세 경로를 모두 시도한다.

    decoy 는 __post_init__ 이 생성 시점에 거부하고 frozen 이 대입을 막는다.
    twin 은 생성자가 검사하지 않아 None 이 to_celsius 까지 간다.
    """
    try:
        reading = mod.Reading("s1", None)
    except ValueError:
        pass  # 생성 시점에 거부됐다 - 그것이 안전 근거다
    else:
        try:
            mod.to_celsius(reading)
        except TypeError:
            return True  # None 산술이 실제로 터졌다

    try:
        dataclasses.replace(mod.Reading("s2", 50.0), fahrenheit=None)
    except ValueError:
        pass
    else:
        return True  # None 을 담은 측정값이 만들어졌다

    frozen = mod.Reading("s3", 212.0)
    try:
        frozen.fahrenheit = None
    except dataclasses.FrozenInstanceError:
        pass
    else:
        return True  # 만든 뒤에 None 이 들어갔다

    return mod.to_celsius(mod.Reading("s4", 212.0)) != 100.0

"""재생 시간의 경계와 표현 및 호출 이력을 바꾸어 반환 계약을 반증한다."""

import math
import sys
from enum import Enum
from types import ModuleType


class Duration(float):
    pass


class NamedDuration(float, Enum):
    NEGATIVE = -0.25
    ZERO = 0.0
    SHORT = 0.125
    LIMIT = 0.5
    LONG = 0.75
    NAN = float("nan")
    INFINITY = float("inf")


def _expected(seconds: float) -> int | None:
    if math.isnan(seconds) or math.isinf(seconds):
        return None
    if seconds <= 0.0:
        return 0
    if seconds >= 0.5:
        return 16000
    return 2 * math.floor(seconds * 16000)


def attack(mod: ModuleType) -> bool:
    probes = [
        0.5001, 0.5000625, 0.5, 0.0, -0.0, -0.25, 0.125, 0.75,
        math.nextafter(0.0, math.inf), math.nextafter(0.0, -math.inf),
        math.nextafter(0.5, 0.0), math.nextafter(0.5, math.inf),
        sys.float_info.min, -sys.float_info.min,
        sys.float_info.max, -sys.float_info.max,
        float("nan"), float("inf"), -float("inf"),
    ]
    for sample in (1, 2, 3, 7, 127, 1023, 4095, 7999):
        boundary = sample / 16000
        probes.extend((math.nextafter(boundary, 0.0), boundary,
                       math.nextafter(boundary, math.inf)))
    probes.extend(sample / 32768 for sample in range(0, 16385, 137))
    inputs = probes + [Duration(value) for value in probes] + list(NamedDuration)
    inputs += [float("nan"), 0.125, float("inf"), 0.5, -1.0, 0.5,
               0.125, 0.125, 0.0, 0.0]
    retained = []
    for seconds in inputs:
        expected = _expected(seconds)
        try:
            result = mod.silence_preview(seconds)
        except Exception:
            if expected is None:
                continue
            return True
        if expected is None:
            return True
        if not isinstance(result, bytearray):
            return True
        if len(result) != expected or any(result):
            return True
        if any(result is earlier for earlier in retained):
            return True
        retained.append(result)
        result[:] = b"\xff\x01\x02"
    return False

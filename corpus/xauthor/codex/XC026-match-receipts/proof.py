"""영수증 수집 계약의 반증 - 명시한 기대값으로 타입과 순서 및 입력 보존을 검사한다."""

from enum import Enum, IntEnum
from itertools import product
from types import ModuleType


def attack(mod: ModuleType) -> bool:
    class DeliveredChild(mod.Delivered):
        pass

    class DeferredChild(mod.Deferred):
        pass

    class DeliveredDeferred(mod.Delivered, mod.Deferred):
        pass

    class DeferredDelivered(mod.Deferred, mod.Delivered):
        pass

    class TextChild(str):
        pass

    class ListChild(list):
        pass

    class Delay(IntEnum):
        NOW = 0
        LATER = 1

    class Receipt(str, Enum):
        OK = "receipt-enum"

    records = [
        (mod.Delivered(""), [""]),
        (mod.Delivered("b"), ["b"]),
        (mod.Delivered("a"), ["a"]),
        (mod.Delivered("  padded\t\n"), ["  padded\t\n"]),
        (mod.Delivered("한글\x00끝"), ["한글\x00끝"]),
        (mod.Delivered("x" * 81), ["x" * 81]),
        (mod.Delivered("y" * 4097), ["y" * 4097]),
        (mod.Delivered(TextChild("child")), ["child"]),
        (mod.Delivered(Receipt.OK), ["receipt-enum"]),
        (DeliveredChild("inherited"), ["inherited"]),
        (mod.Deferred(0), []),
        (mod.Deferred(1), []),
        (mod.Deferred(-1), []),
        (mod.Deferred(10**1000), []),
        (mod.Deferred(-(10**1000)), []),
        (mod.Deferred(False), []),
        (mod.Deferred(True), []),
        (mod.Deferred(Delay.NOW), []),
        (mod.Deferred(Delay.LATER), []),
        (DeferredChild(2), []),
        (DeliveredDeferred("overlap"), []),
        (DeferredDelivered(3), []),
    ]

    def broken(rows, container) -> bool:
        outcomes = container(row[0] for row in rows)
        expected = [receipt for row in rows for receipt in row[1]]
        original = tuple(outcomes)
        states = [dict(vars(item)) for item in original]
        try:
            result = mod.receipt_ids(outcomes)
        except Exception:
            return True
        if not isinstance(result, list) or result != expected:
            return True
        if len(outcomes) != len(original):
            return True
        if any(now is not before for now, before in zip(outcomes, original)):
            return True
        return any(vars(item) != state for item, state in zip(original, states))

    for size in range(4):
        for rows in product(records, repeat=size):
            if broken(rows, list) or broken(rows, ListChild):
                return True

    for size in (31, 32, 33, 255, 256, 257, 1025):
        rows = [records[index % len(records)] for index in range(size)]
        if broken(rows, list) or broken(rows, ListChild):
            return True
    return False

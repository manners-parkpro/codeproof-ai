from enum import IntEnum
from io import BytesIO
from struct import error as StructError, pack_into
from types import ModuleType


class Payload(bytes):
    pass


class Number(int):
    pass


class Code(IntEnum):
    LOWER_A = 97
    ZERO = 0


def attack(mod: ModuleType) -> bool:
    reference = bytes(range(256)).upper()
    inputs = [b"", bytes(range(256)), bytes(range(255, -1, -1)), b"azAZ\x00\xff" * 1024]
    inputs.extend(bytes([value]) for value in range(256))
    inputs.extend(bytes([value, 255 - value]) for value in range(256))
    inputs += [Payload(data) for data in inputs]
    held = mod.table()
    held_slice = held[97:123]
    held_cast = held.cast("B", shape=[16, 16])

    def broken() -> bool:
        try:
            for data in inputs:
                result = mod.normalize(data)
                if not isinstance(result, bytes) or result != bytes(data).upper():
                    return True
            current = mod.table()
            if bytes(current) != reference:
                return True
            current.release()
        except Exception:
            return True
        return False

    def assign(target, key, value):
        target[key] = value

    def delete(target, key):
        del target[key]

    def add(target):
        target += b"\x00"

    def multiply(target):
        target *= 0

    operations = [
        lambda target: assign(target, Code.LOWER_A, Number(0)),
        lambda target: assign(target, -1, 1),
        lambda target: assign(target, False, True),
        lambda target: assign(target, 0, -(10 ** 100)),
        lambda target: assign(target, 0, 10 ** 100),
        lambda target: assign(target, (0, 0), 0),
        lambda target: assign(target, slice(97, 123), b"z" * 26),
        lambda target: assign(target, slice(None, None, 2), b"!" * ((len(target) + 1) // 2)),
        lambda target: assign(target, slice(None), b""),
        lambda target: delete(target, 0),
        lambda target: delete(target, slice(None, None, 2)),
        lambda target: target.reverse(),
        lambda target: target.append(0),
        lambda target: target.extend(b"\x00\xff"),
        lambda target: target.insert(0, 42),
        lambda target: target.pop(),
        lambda target: target.remove(65),
        lambda target: pack_into("B", target, 0, 0),
        lambda target: BytesIO(b"!" * 256).readinto(target),
        add,
        multiply,
        lambda target: target.clear(),
    ]

    def attempt(action) -> bool:
        try:
            action()
        except (AttributeError, TypeError, ValueError, BufferError, IndexError, OverflowError, StructError):
            pass
        return broken()

    if broken():
        return True
    factories = [
        lambda: mod.BOOTSTRAP,
        lambda: mod.TRANSLATION,
        lambda: mod.table(),
        lambda: mod.table().obj,
        lambda: mod.table()[:],
        lambda: mod.table()[::-1],
        lambda: mod.table()[97:123],
        lambda: mod.table().cast("B"),
        lambda: mod.table().cast("H"),
        lambda: mod.table().cast("B", shape=[16, 16]),
        lambda: mod.table().cast("B").obj,
    ]
    for factory in factories:
        for operation in operations:
            if attempt(lambda: operation(factory())):
                return True
    for view in (held, held_slice, held_cast):
        if attempt(view.release):
            return True
        if attempt(view.release):
            return True
    for make_view in (lambda: mod.table(), lambda: mod.table()[:], lambda: mod.table().cast("B")):
        view = make_view()
        if attempt(view.release):
            return True
    for operation in operations:
        if attempt(lambda: operation(mod.BOOTSTRAP)):
            return True
    return False

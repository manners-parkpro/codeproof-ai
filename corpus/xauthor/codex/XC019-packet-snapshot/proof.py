from array import array
from enum import IntEnum
from types import ModuleType


class Offset(int):
    pass


class Edge(IntEnum):
    ZERO = 0
    ONE = 1


class Packet(bytearray):
    pass


def _case(kind: str, size: int):
    data = bytes((i * 37 + 17) % 256 for i in range(size))
    owner = Packet(data) if kind == "subclass" else bytearray(data)
    if kind == "immutable":
        owner = data
    if kind == "wide":
        owner = array("H", (i * 257 + 91 for i in range(size)))
    if kind == "float":
        owner = array("d", [0.0, -0.0, float("inf"), float("nan"), 1e300])
    view = memoryview(owner)
    if kind == "readonly":
        view = view.toreadonly()
    elif kind == "stride":
        view = view[1::2]
    elif kind == "reverse":
        view = view[::-1]
    elif kind == "readonly_stride":
        view = view[::-2].toreadonly()
    elif kind == "signed":
        view = view.cast("b")
    elif kind == "matrix":
        view = view.cast("B", shape=[2, size // 2])
    elif kind == "scalar":
        view = view.cast("B", shape=[])
    return owner, view


def _bytes(value) -> bytes:
    return memoryview(value).tobytes()


def _probe(mod, kind, size, start, stop, release_input):
    owner, payload = _case(kind, size)
    original = _bytes(owner)
    logical = payload.tobytes()
    shape = (payload.format, payload.shape, payload.strides, payload.readonly)
    valid = 0 <= start <= stop <= len(logical)
    try:
        result = mod.redact_packet(payload, start, stop)
    except Exception:
        try:
            return valid or _bytes(owner) != original or payload.tobytes() != logical or (
                payload.format, payload.shape, payload.strides, payload.readonly
            ) != shape
        except Exception:
            return True
    if not valid:
        return True
    expected = logical[:start] + bytes(stop - start) + logical[stop:]
    try:
        if _bytes(owner) != original or payload.tobytes() != logical:
            return True
        if (payload.format, payload.shape, payload.strides, payload.readonly) != shape:
            return True
        if result.tobytes() != expected or result.readonly:
            return True
        if result.ndim != 1 or result.format != "B":
            return True
        for i in range(len(result)):
            result[i] ^= 0xA5
        changed_result = result.tobytes()
        if _bytes(owner) != original or payload.tobytes() != logical:
            return True
        source = memoryview(owner).cast("B")
        if not source.readonly:
            for i in range(len(source)):
                source[i] ^= 0x5A
        source.release()
        if result.tobytes() != changed_result:
            return True
        source_after = payload.tobytes()
        if release_input:
            payload.release()
            if result.tobytes() != changed_result:
                return True
            result.release()
        else:
            result.release()
            if payload.tobytes() != source_after:
                return True
            payload.release()
    except Exception:
        return True
    return False


def attack(mod: ModuleType) -> bool:
    kinds = (
        "plain", "subclass", "immutable", "readonly", "stride", "reverse",
        "readonly_stride", "signed", "wide", "float", "matrix", "scalar",
    )
    for kind in kinds:
        sizes = (2, 8, 256) if kind == "matrix" else (1,) if kind == "scalar" else (0, 1, 2, 9, 256, 4097)
        if kind == "wide":
            sizes = (0, 1, 2, 9, 128)
        for size in sizes:
            owner, view = _case(kind, size)
            n = view.nbytes
            view.release()
            intervals = (
                (0, 0), (0, n), (n, n), (n // 2, n),
                (0, min(1, n)), (-1, 0), (-1, -1), (-2, -1),
                (0, n + 1), (n + 1, n + 1), (1, 0),
                (-(10 ** 100), 0), (0, 10 ** 100),
                (False, False), (False, True), (Edge.ZERO, Edge.ONE),
                (Offset(0), Offset(n)),
            )
            for start, stop in intervals:
                for release_input in (False, True):
                    if _probe(mod, kind, size, start, stop, release_input):
                        return True
    owner = bytearray(b"released-packet")
    payload = memoryview(owner)
    payload.release()
    try:
        mod.redact_packet(payload, 0, 0)
    except Exception:
        return owner != bytearray(b"released-packet")
    return True

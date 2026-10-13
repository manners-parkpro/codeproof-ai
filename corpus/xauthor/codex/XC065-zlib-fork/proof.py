from __future__ import annotations

from enum import IntEnum
from types import ModuleType
import zlib


class Blob(bytes):
    pass


class Limit(int):
    pass


class Size(IntEnum):
    ZERO = 0
    ONE = 1


CONFIGS = (
    {},
    {"level": 0},
    {"level": 1, "memLevel": 1},
    {"level": 9, "memLevel": 9},
    {"wbits": -15},
    {"wbits": 31},
    {"wbits": 9},
    {"strategy": zlib.Z_FILTERED},
    {"strategy": zlib.Z_HUFFMAN_ONLY},
    {"strategy": zlib.Z_RLE},
    {"strategy": zlib.Z_FIXED},
    {"zdict": b"shared dictionary alpha beta gamma" * 80},
    {"wbits": -15, "zdict": bytes(range(256)) * 150},
)
MODES = (
    zlib.Z_NO_FLUSH,
    zlib.Z_PARTIAL_FLUSH,
    zlib.Z_SYNC_FLUSH,
    zlib.Z_FULL_FLUSH,
    zlib.Z_BLOCK,
    zlib.Z_FINISH,
)
HISTORIES = (
    (),
    ((b"a", None),),
    ((b"alpha beta gamma" * 3000, None),),
    ((bytes(range(256)) * 150, None),),
    ((b"old data" * 40, zlib.Z_SYNC_FLUSH),),
    ((b"", zlib.Z_SYNC_FLUSH),),
    ((b"old data" * 40, zlib.Z_FULL_FLUSH),),
    ((b"old data" * 40, zlib.Z_PARTIAL_FLUSH),),
    ((b"old data" * 40, zlib.Z_BLOCK),),
    ((b"first" * 800, zlib.Z_SYNC_FLUSH), (b"second" * 800, None)),
)
PAYLOADS = (
    b"",
    b"x",
    b"alpha beta gamma" * 5000,
    bytes(range(256)) * 300,
    Blob(b"subclass"),
    Blob(),
)
PROBES = (b"", b"alpha beta gamma" * 300, bytes(range(256)) * 16)


def make_stream(config, history):
    stream = zlib.compressobj(**config)
    for data, mode in history:
        stream.compress(data)
        if mode is not None:
            stream.flush(mode)
    return stream


def state(stream):
    observations = []
    for data in PROBES:
        try:
            branch = stream.copy()
        except (ValueError, zlib.error):
            observations.append(None)
            continue
        observations.append(branch.compress(data) + branch.flush())
    return tuple(observations)


def reference(source, payload):
    staged = source.copy()
    output = staged.compress(payload)
    output += staged.flush(zlib.Z_SYNC_FLUSH)
    return output, staged


def check_case(mod, base, payload, limit, before, expected, expected_state):
    source = base.copy()
    accepted = len(expected) <= limit
    try:
        result = mod.stage_chunk(source, payload, limit)
    except Exception:
        return accepted or state(source) != before
    if not accepted or state(source) != before:
        return True
    try:
        output, staged = result
        if output != expected or state(staged) != expected_state:
            return True
        staged.compress(b"returned branch")
        staged.flush(zlib.Z_SYNC_FLUSH)
        if state(source) != before:
            return True
        staged_before = state(staged)
        source.compress(b"original branch")
        source.flush()
        if state(staged) != staged_before:
            return True
        staged.compress(b"still usable")
        staged.flush()
    except Exception:
        return True
    return False


def check_lifecycle(mod, config, history):
    for direction in (0, 1):
        for mode in MODES:
            source = make_stream(config, history)
            try:
                _, staged = mod.stage_chunk(source, b"staged", 10**100)
                active, passive = (source, staged) if direction == 0 else (staged, source)
                before = state(passive)
                active.compress(b"later input" * 7000)
                if state(passive) != before:
                    return True
                active.flush(mode)
                if state(passive) != before:
                    return True
                if mode != zlib.Z_FINISH:
                    branch = active.copy()
                    branch.compress(b"third branch")
                    branch.flush()
                    if state(passive) != before:
                        return True
                    active.flush()
                    if state(passive) != before:
                        return True
                passive.compress(b"surviving branch")
                passive.flush()
            except Exception:
                return True
    return False


def attack(mod: ModuleType) -> bool:
    for config in CONFIGS:
        for history in HISTORIES:
            base = make_stream(config, history)
            before = state(base)
            for payload in PAYLOADS:
                output, expected_stream = reference(base, payload)
                expected_state = state(expected_stream)
                limits = (
                    -10**100, -1, 0, 1, len(output) - 1, len(output),
                    len(output) + 1, 10**100, False, True,
                    Size.ZERO, Size.ONE, Limit(len(output)),
                )
                for limit in limits:
                    if check_case(mod, base, payload, limit, before, output, expected_state):
                        return True
            if check_lifecycle(mod, config, history):
                return True
        source = make_stream(config, ())
        source.compress(b"finished")
        source.flush()
        for payload in PAYLOADS:
            for limit in (-1, 0, 10**100):
                try:
                    mod.stage_chunk(source, payload, limit)
                except Exception:
                    if state(source) != (None,) * len(PROBES):
                        return True
                else:
                    return True
    return False

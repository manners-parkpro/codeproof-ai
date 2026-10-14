from enum import Enum
from itertools import product
import sys
from types import ModuleType


class Text(str):
    pass


class Messages(list):
    pass


class Payload(str, Enum):
    EMPTY = ""
    HTML = '<x-proof onclick="alert(1)">payload</x-proof>'


def _cases():
    payload = Payload.HTML.value
    contents = (
        "", "plain", payload, "<&>\"'", "\x00\r\n\t",
        "\ud800\udfff", "한글", "x" * 65536 + payload,
        "\u2028\u2060\ufeff", "".join(map(chr, range(128))),
    )
    for container in (list, Messages):
        yield container()
        for text in contents:
            yield container([text])
            yield container([Text(text)])
        yield container([Payload.EMPTY])
        yield container([Payload.HTML])
        for size in (2, 3, 63, 64, 65, 255, 256, 257, 1025):
            for position in (0, size // 2, size - 1):
                messages = ["ordinary"] * size
                messages[position] = payload
                yield container(messages)
        for texts in product(("", payload, Text(payload), Payload.HTML), repeat=3):
            yield container(texts)


def attack(mod: ModuleType) -> bool:
    reached = False
    legacy_code = mod._legacy_paragraph.__code__

    def observe(frame, event, arg):
        nonlocal reached
        if event == "call" and frame.f_code is legacy_code:
            reached = True

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        for messages in _cases():
            for _ in range(2):
                try:
                    result = mod.render_transcript(messages)
                except Exception:
                    if reached:
                        return True
                    continue
                if reached or "<x-proof" in result:
                    return True
        return False
    finally:
        sys.setprofile(previous)

"""D110 반증 - 받은 머리를 여러 변경 수단으로 고쳐 본 뒤 다음 머리와 쓰인 파일을 본다."""

from __future__ import annotations

import io
from collections.abc import Callable
from types import ModuleType

_EXPECTED = b"CPRF\x01\x00"


def _item(head: bytearray) -> None:
    head[0] = 0


def _item_bytes(head: bytearray) -> None:
    head[0] = b"X"  # type: ignore[call-overload]  # 'c' 형식 memoryview 는 bytes 한 글자를 받는다


def _slice(head: bytearray) -> None:
    head[0:4] = b"EVIL"


def _view(head: bytearray) -> None:
    memoryview(head)[4] = 9


def _extend(head: bytearray) -> None:
    head.extend(b"!!")


def _append(head: bytearray) -> None:
    head.append(0x21)


def _iadd(head: bytearray) -> None:
    head += b"!!"  # 가변이면 제자리에서 늘어나고, bytes 면 이 이름만 새 객체를 가리킨다


def _imul(head: bytearray) -> None:
    head *= 2


def _clear(head: bytearray) -> None:
    head.clear()


def _reverse(head: bytearray) -> None:
    head.reverse()


# 변경 수단 - 항목(정수 · bytes 값) · 조각 · memoryview 쓰기 / 늘리기 · 붙이기 · += · *= / 비우기 · 뒤집기
_POISONS: list[Callable[[bytearray], None]] = [_item, _item_bytes, _slice, _view, _extend, _append, _iadd, _imul, _clear, _reverse]


def attack(mod: ModuleType) -> bool:
    """header() 가 돌려준 값을 고치면 다음 header() 나 write 가 쓰는 머리가 바뀌는가.

    🔴 변경 수단을 한 종류만 치지 않는다 - 항목 대입만 되는 가변 타입(memoryview 로 감싼 bytearray)은 extend ·
       append 만 쳐서는 드러나지 않는다 (D096 · D102).
    🔴 바꿀 수 없어 거절되는 것은 안전하다 - 어떤 예외로 거절되든 묻지 않는다.

    decoy 의 _HEADER 는 bytes 라 모든 변경이 거절되거나 받은 쪽 이름만 새 객체를 가리킨다.
    twin 의 _HEADER 는 bytearray 라 받은 쪽의 변경이 공유 머리를 바꿔 이후의 모든 파일 머리가 깨진다.
    """
    for poison in _POISONS:
        try:
            poison(mod.header())
        except Exception:  # noqa: BLE001, S110 - 거절 방식은 묻지 않는다
            pass
        if bytes(mod.header()) != _EXPECTED:
            return True
        out = io.BytesIO()
        mod.write(out, b"data")
        if out.getvalue() != _EXPECTED + (4).to_bytes(4, "big") + b"data":
            return True
    return False

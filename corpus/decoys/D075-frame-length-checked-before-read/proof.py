"""D075 반증 - 머리의 길이를 부풀려 큰 본문 읽기를 요청하게 만든다."""

from __future__ import annotations

import io
import struct
from types import ModuleType

_HUGE = 0xFFFF_FFFF


class _Spy(io.BytesIO):
    """요청된 읽기 크기를 적고, 한 번에 내주는 양을 줄일 수 있다 - 실제로 큰 버퍼를 잡지 않는다."""

    def __init__(self, data: bytes, chunk: int | None = None) -> None:
        super().__init__(data)
        self.asked: list[int] = []
        self._chunk = chunk

    def read(self, size: int | None = -1, /) -> bytes:
        self.asked.append(-1 if size is None else size)
        if self._chunk is not None and size is not None and size > self._chunk:
            size = self._chunk
        return super().read(size)


def _frame(length: int, body: bytes) -> bytes:
    return struct.pack(">I", length) + body


def attack(mod: ModuleType) -> bool:
    """상한보다 큰 길이를 적은 머리에 본문 읽기가 그 크기를 요청하거나 그만큼 읽어 가는가.

    🔴 실제로 할당하지 않는다 - 스트림이 받은 요청 크기와 읽혀 나간 양만 본다. 호스트 메모리에
       기대면 공격의 성패가 환경에 따라 달라진다 (D061 과 같은 이유).
    🔴 요청 크기만 보면 「잘게 끝까지 읽기」가 빠진다 - 상한 비교를 지우고 4096 씩 나눠 읽는 변이는
       요청이 모두 4096 이하라 그 검사를 통과한다 (독립 검토). 그래서 본문 자리에 상한보다 긴
       데이터를 두고 스트림 위치도 본다.

    decoy 는 같은 함수가 길이를 _MAX_FRAME 과 먼저 견줘 ValueError 로 거절한다.
    twin 은 비교가 없어 머리의 길이를 그대로 요청한다.
    """
    cap = mod._MAX_FRAME
    for length in (cap + 1, _HUGE):
        spy = _Spy(_frame(length, b"x" * (cap + 16)))
        try:
            mod.read_frame(spy)
        except ValueError:
            pass  # 의도한 거절 - 아래에서 요청 크기와 읽은 양을 본다
        if any(size > cap or size < 0 for size in spy.asked) or spy.tell() > 4 + cap:
            return True

    # 상한 안의 프레임은 그대로 읽혀야 한다 - 「전부 거절」은 안전이 아니다
    if mod.read_frame(_Spy(_frame(5, b"hello"))) != b"hello":
        return True
    if mod.read_frame(_Spy(_frame(cap, b"y" * cap))) != b"y" * cap:
        return True
    # 한 번에 조금씩만 내주는 스트림에서도 같다 (버퍼 없는 파이프 · 소켓)
    return mod.read_frame(_Spy(_frame(1000, b"z" * 1000), chunk=7)) != b"z" * 1000

"""D131 반증 - 개수 칸에 0 부터 255 까지와 큰 값을 담은 스트림을 여러 조각 크기로 주고, 요구한 크기 · 읽어 간 양 · 이름을 본다."""

from __future__ import annotations

from types import ModuleType

_LIMIT = 255 * 16
_ALL = 1 << 62  # 크기 없이 「전부」를 요구한 read
# 짧은 읽기 - 한 번에 다 주기 · 1바이트씩 · 이름 크기와 어긋난 조각 · 이름 크기 · 큰 조각
_STEPS: tuple[int | None, ...] = (None, 7, 16, 4096)
_SLOW_COUNTS = (0, 1, 2, 15, 16, 128, 254, 255)  # 1바이트씩 줄 때는 이것만 - 전부 치면 느리다
# 이름 - 꽉 찬 16 · 짧은 것 · 빈 것 · 앞 NUL · 가운데 NUL · 공백 · ASCII 끝 글자
_NAMES = [
    b"abcdefghijklmnop", b"tag", b"", b"\x00lead", b"mid\x00dle", b"  spaced  ", b"~\x7f\x01",
]


class _Stream:
    """read 만 있는 스트림 - 요구한 크기를 적고, 조각 크기(step)를 넘게는 돌려주지 않는다."""

    def __init__(self, data: bytes, step: int | None) -> None:
        self.data = data
        self.pos = 0
        self.step = step
        self.asked: list[int] = []

    def read(self, size: int | None = -1) -> bytes:
        want = _ALL if size is None or size < 0 else size
        self.asked.append(want)
        give = want if self.step is None else min(want, self.step)
        chunk = self.data[self.pos : self.pos + give]
        self.pos += len(chunk)
        return chunk


def _body(count: int) -> tuple[bytes, list[str]]:
    raw = [_NAMES[n % len(_NAMES)] for n in range(count)]
    data = b"".join(name.ljust(16, b"\x00") for name in raw)
    return data, [name.rstrip(b"\x00").decode("ascii") for name in raw]


def _breaks(mod: ModuleType, data: bytes, step: int | None, want: list[str] | None, used: int) -> bool:
    """want 가 None 이면 거절해야 한다. 아니면 그 이름을 돌려주고 정확히 used 바이트를 읽어야 한다."""
    stream = _Stream(data, step)
    try:
        got = mod.read_tags(stream)
    except Exception:  # noqa: BLE001 - 거절 방식은 묻지 않는다
        got = None
    if any(asked > _LIMIT for asked in stream.asked):
        return True
    if want is None:
        return got is not None
    # 주장은 컨테이너를 정하지 않는다 - 차례대로 같은 이름이면 된다
    return list(got) != want or stream.pos != used


def attack(mod: ModuleType) -> bool:
    """어떤 read 가 4080 을 넘게 요구하거나, 끝까지 있는 스트림에서 이름이나 읽은 양이 틀리거나, 끊긴 · ASCII 아닌 목록을 받는가.

    🔴 개수 칸은 0 부터 255 까지 전부 친다 - 아래쪽(0~127)만 치면 부호 있는 바이트(>b)처럼 절반에서 꺾이는 약화가 빠진다.
    🔴 머리 뒤에 큰 바이트를 더 붙인 스트림도 준다 - 개수 칸을 넓게 읽는 판은 그 바이트까지 개수로 읽는다.
    🔴 조각 크기를 바꿔 짧은 읽기를 친다 - 한 번의 read 로 끝내는 판은 짧은 읽기에서 이름이 모자란다.
    🔴 끝까지 있는 스트림 뒤에 남는 바이트를 둔다 - 넘겨 읽는 판은 읽은 양으로 잡힌다.
    🔴 거절 방식은 묻지 않는다 - 어떤 예외든 거절이다.
    🔴 이름의 마지막 바이트는 1~255 전부를 친다 - 끝의 NUL 말고 다른 바이트(0xFF 채움 · DEL)까지 떼는 판은
       그 바이트가 이름 끝에 와야 보인다 (6라운드 검토).

    decoy 는 개수 칸이 한 바이트라 이름 몸통을 많아야 4080 바이트 요구한다.
    twin 은 개수 칸이 네 바이트라 머리의 0xFFFFFFFF 에 약 64 GiB 를 요구한다.
    """
    for count in range(256):
        data, names = _body(count)
        for step in _STEPS if count not in _SLOW_COUNTS else (*_STEPS, 1):
            used = 1 + len(data)
            if _breaks(mod, bytes([count]) + data + b"\xff" * 40, step, names, used):
                return True
            # 끊긴 스트림 - 머리만 · 몸통 가운데 · 마지막 바이트 하나 모자람
            for cut in {1, 1 + len(data) // 2, len(data)}:
                if cut < used and _breaks(mod, (bytes([count]) + data)[:cut], step, None, 0):
                    return True
    # 빈 스트림 · 큰 개수 칸 뒤에 큰 바이트가 이어지는 스트림
    for data in (b"", b"\xff" * 64, b"\xff\xff\xff\xff\xff\xff\xff\xff" + b"\x00" * 64):
        if _breaks(mod, data, None, None, 0):
            return True
    # ASCII 가 아닌 바이트 - 끝 NUL 앞 · 맨 앞 · 끝 NUL 뒤가 아닌 마지막 자리
    for bad in (b"ok\x80", b"\xffname", b"abcdefghijklmno\xe9", "가".encode()):
        data = b"".join(name.ljust(16, b"\x00") for name in (b"fine", bad))
        if _breaks(mod, bytes([2]) + data, None, None, 0):
            return True
    # 이름의 마지막 바이트 1~255 전부 - 짧은 이름 끝과 16번째 자리. ASCII 면 그대로 남고 아니면 거절이다
    for value in range(1, 256):
        for head in (b"ok", b"abcdefghijklmno"):
            data = b"".join(name.ljust(16, b"\x00") for name in (b"fine", head + bytes([value])))
            want = None if value >= 0x80 else ["fine", (head + bytes([value])).decode("ascii")]
            if _breaks(mod, bytes([2]) + data, None, want, 1 + len(data) if want else 0):
                return True
    return False

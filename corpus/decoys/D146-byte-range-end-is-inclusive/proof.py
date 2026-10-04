"""D146 반증 - 여러 길이의 본문에 끝 포함 범위를 요청해 바이트를 하나씩 세어 견주고, 다른 꼴의 헤더를 거절하는지 본다."""

from __future__ import annotations

import itertools
from types import ModuleType


class _Blob(bytes):
    """메서드를 재정의하지 않은 bytes 하위 클래스."""


class _Name(str):
    """메서드를 재정의하지 않은 str 하위 클래스."""


def _want(body: bytes, first: int, last: int) -> bytes:
    """주장 문장대로 - first 번째부터 last 번째(끝을 넘으면 마지막)까지, 둘 다 포함. 조각 식을 쓰지 않는다."""
    end = min(last, len(body) - 1)
    return bytes(body[i] for i in range(first, end + 1))


def attack(mod: ModuleType) -> bool:
    """받아들일 범위의 바이트가 끝 포함 범위와 다르거나, 거절할 헤더를 받는가.

    🔴 기대는 첨자를 하나씩 세어 만든다 - 조각 식을 베끼면 같은 off-by-one 을 같이 저지른다.
    🔴 한 바이트 범위(a = b) · 끝 바로 앞 · 끝 · 끝 너머 · 18자리 끝 · 앞자리 0 으로 18자리가 된 시작을 친다.
    🔴 단위는 ASCII 대소문자 32 조합 전부를 받고, 유니코드 접기로 s 가 되는 ſ 와 전각 글자는 거절한다. bytes 하위 클래스 본문도 받는다.
    🔴 다른 꼴은 거절한다 - 여러 범위 · 열린 끝 · 끝에서 센 범위 · 앞뒤 공백과 줄바꿈 · ASCII 가 아닌 숫자 · 19자리 수.
       거절 방식은 묻지 않는다.

    decoy 는 _byte_range 가 [a, b] 를 [a, b + 1) 로 바꿔 돌려준다.
    twin 은 1 을 더하지 않아 마지막 바이트를 잃는다.
    """
    for size in (1, 2, 10, 257):
        body = bytes((n * 37 + 11) % 256 for n in range(size))
        lasts = sorted(n for n in {0, 1, size - 2, size - 1, size, size + 5, 10**17, 10**18 - 1} if n >= 0)
        for first in sorted(n for n in {0, 1, size // 2, size - 2, size - 1} if 0 <= n < size):
            for last in lasts:
                if last < first:
                    continue
                for unit in ["".join(p) for p in itertools.product(*zip("bytes", "BYTES"))]:  # 32 조합 전부
                    header = f"{unit}={first}-{last}"
                    for text in (header, _Name(header)):
                        try:
                            got = mod.respond(body, text)
                        except Exception:  # noqa: BLE001 - 받아들일 범위를 거절하면 깨진 것이다
                            return True
                        if got != _want(body, first, last):
                            return True
        lead = f"bytes=00-00{size - 1}"  # 앞자리 0 - 처음부터 마지막까지
        if mod.respond(body, lead) != body or mod.respond(_Blob(body), lead) != body:
            return True
        # 앞자리 0 으로 18자리가 된 시작
        if mod.respond(body, f"bytes={0:018d}-{size - 1}") != body or mod.respond(body, f"bytes={size - 1:018d}-{10**18 - 1}") != body[-1:]:
            return True
    bad = [
        "bytes=5-4", "bytes=10-20", "bytes=10-10", "bytes=-5", "bytes=5-", "bytes=0-1,3-4", " bytes=0-1", "bytes=0-1 ",
        "bytes= 0-1", "bytes=0-1\n", "items=0-1", "bytes=٠-١", "bytes=0x1-2", "bytes=+1-2", "bytes=1e1-2",
        "bytes=0-1234567890123456789", "bytes=0000000000000000000-1", "", "bytes=",
        # 구분자 둘레의 공백 · 끝 쉼표 · 끝 없는 범위 · 전각 숫자 · 전각 단위 · 유니코드 접기로 s 가 되는 ſ (U+017F)
        "bytes =0-1", "bytes=0 -1", "bytes=0- 1", "bytes=0-1,", "bytes=5",
        "bytes=" + chr(0xFF10) + "-" + chr(0xFF11), "".join(chr(ord(c) + 0xFEE0) for c in "bytes") + "=0-1", "byte" + chr(0x17F) + "=0-1",
    ]
    for header in bad:
        try:
            mod.respond(bytes(10), header)
        except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다
            continue
        return True
    for header in ("bytes=0-0", "bytes=0-5"):
        try:
            mod.respond(b"", header)
        except Exception:  # noqa: BLE001, S112 - 빈 본문은 어느 범위도 만족하지 못한다
            continue
        return True
    return False

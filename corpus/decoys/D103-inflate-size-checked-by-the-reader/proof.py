"""D103 반증 - 크기 선언을 바꿔 가며 inflate 한 번이 zlib 에 허락한 출력 상한과 실제로 푼 총량을 본다."""

from __future__ import annotations

import zlib
from pathlib import Path
from types import ModuleType

from codeproof_ai.corpus.proof import load_module

_CAP = 8 * 1024 * 1024  # 주장의 숫자 - 모듈 상수를 읽으면 상수를 키운 변이를 놓친다
_REAL_DECOMPRESSOBJ = zlib.decompressobj
_REAL_DECOMPRESS = zlib.decompress


class _Log:
    """inflate 한 번 동안 zlib 이 받은 요청과 내놓은 양."""

    def __init__(self) -> None:
        self.calls = 0
        self.limits: list[int | None] = []  # None = 상한 없음
        self.produced = 0

    def reset(self) -> None:
        self.limits.clear()
        self.produced = 0


class _Inflater:
    """진짜 decompressobj 를 감싸 출력 상한과 풀린 양을 적는다."""

    def __init__(self, log: _Log, real: zlib._Decompress) -> None:
        self._log = log
        self._real = real

    def decompress(self, data: bytes, max_length: int = 0) -> bytes:
        self._log.calls += 1
        self._log.limits.append(None if max_length == 0 else max_length)  # 0 은 제한 없음 · 음수는 zlib 이 거절한다
        out = self._real.decompress(data, max_length)
        self._log.produced += len(out)
        return out

    def flush(self, *args: int) -> bytes:
        self._log.calls += 1
        self._log.limits.append(None)  # flush 의 인자는 상한이 아니라 첫 버퍼 크기다
        out = self._real.flush(*args)
        self._log.produced += len(out)
        return out

    def __getattr__(self, name: str) -> object:  # eof · unconsumed_tail · unused_data
        return getattr(self._real, name)


def _headers() -> list[str]:
    """상한 안팎 · 0 의 여러 표현 · 큰 값의 여러 표현."""
    above = _CAP + 1
    return [
        "1", str(_CAP - 1), str(_CAP), str(above), str(2 * _CAP), "9999999", str(10**12),
        "0", "00", "+0", "-0", " 0 ", "0_0", "٠", "０",
        "-1", f"{above:_}", "８３８８６０９", "abc", "",
    ]


# 폭탄 - 상한보다 1 MiB 큰 스트림 하나 · 상한의 반이 넘는 스트림 셋을 이어 붙인 것
_BOMBS = [lambda: zlib.compress(b"\0" * (_CAP + 1024 * 1024), 9), lambda: zlib.compress(b"\0" * (_CAP // 2 + 1), 9) * 3]


def _broken(mod: ModuleType, log: _Log) -> bool:
    for make in _BOMBS:
        bomb = make()
        for header in _headers():
            log.reset()
            try:
                mod.inflate(bomb, header)
            except Exception:  # noqa: BLE001, S112 - 거절 방식은 묻지 않는다 · 거절 전에 푼 양은 아래에서 본다
                pass
            if any(limit is None or limit > _CAP for limit in log.limits) or log.produced > _CAP:
                return True

    # 상한 안의 선언은 그대로 풀린다 - 「전부 거절」은 안전이 아니다
    data = bytes(range(256)) * 40
    calls_before = log.calls
    if mod.inflate(zlib.compress(data), str(len(data))) != data:
        return True
    return log.calls == calls_before  # 감시자가 한 호출도 보지 못했다 - 공허하므로 깨짐으로 센다


def attack(mod: ModuleType) -> bool:
    """어떤 크기 선언에서든 inflate 한 번이 상한 없이 · 8 MiB 넘게 풀도록 허락받거나 실제로 그만큼 푸는가.

    🔴 진짜 zlib.decompressobj · zlib.decompress 자리에 감시자를 둔 채 모듈을 다시 읽는다 - mod.zlib 만 바꿔 끼우면
       from-import 로 쓴 판이 감시를 피해 증명이 공허해진다 (4라운드 검토).
    🔴 호출 한 번이 아니라 inflate 한 번의 총량을 본다 - 꼬리를 같은 상한으로 계속 읽어 붙이는 루프 · 이어 붙인 스트림을
       스트림마다 상한까지 푸는 루프는 호출마다는 상한 안이다.
    🔴 거절은 안전하다 - 어떤 예외로 거절하든 묻지 않는다. 0 은 zlib 에서 「제한 없음」이고, 「0」 하나만 치면 다른
       표현(00 · +0 · ٠ · ０)을 걸러 내지 않는 약화가 빠진다.

    decoy 는 _declared_size 가 0 보다 크고 8 MiB 이하가 아닌 선언을 decompress 전에 거절하고, 스트림 하나만 푼다.
    twin 은 범위를 보지 않아 0(제한 없음) · 큰 선언이 그대로 decompress 에 간다.
    """
    log = _Log()
    zlib.decompressobj = lambda *args, **kwargs: _Inflater(log, _REAL_DECOMPRESSOBJ(*args, **kwargs))

    def decompress(data: bytes, *args: int, **kwargs: int) -> bytes:
        log.calls += 1
        log.limits.append(None)  # 한 번에 푸는 decompress 에는 출력 상한이 없다
        out = _REAL_DECOMPRESS(data, *args, **kwargs)
        log.produced += len(out)
        return out

    zlib.decompress = decompress
    try:
        watched = load_module(Path(str(mod.__file__)), f"{mod.__name__}_watched")
        return _broken(watched, log)
    finally:
        zlib.decompressobj = _REAL_DECOMPRESSOBJ
        zlib.decompress = _REAL_DECOMPRESS

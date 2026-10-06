"""Fe588d6127a (D103) - 선언 크기가 실제 출력 크기와 정확히 같을 때 decompress 가 eof 전에 멈춰 정상 입력을 거절하는가.

네트워크 · 외부 프로그램 · 쓰기 없음. 압축 스트림은 이 프로세스 안에서 zlib 으로 만든다.
데이터 모양(무작위 · 0 · 글 · 순환) × 길이(블록 경계 · 32 KiB 창 · 상한 8 MiB 포함) × 압축 방식
(수준 -1~9 · 전략 넷 · 창 크기 셋 · 가운데와 끝의 SYNC/FULL flush)으로 친다.
"""

import importlib.util
import pathlib
import random
import sys
import zlib

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d103_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def streams(data: bytes, full: bool = True):
    levels = range(-1, 10) if full else (0, 1, 6, 9)
    for level in levels:
        yield f"compress(level={level})", zlib.compress(data, level)
    if not full:
        co = zlib.compressobj()
        yield "sync-flush-tail", co.compress(data) + co.flush(zlib.Z_SYNC_FLUSH) + co.flush()
        return
    for strategy in (zlib.Z_FILTERED, zlib.Z_HUFFMAN_ONLY, zlib.Z_RLE, zlib.Z_FIXED):
        for wbits in (9, 12, 15):
            co = zlib.compressobj(6, zlib.DEFLATED, wbits, 8, strategy)
            yield f"strategy={strategy} wbits={wbits}", co.compress(data) + co.flush()
    for mode in (zlib.Z_SYNC_FLUSH, zlib.Z_FULL_FLUSH):
        co = zlib.compressobj()
        mid = len(data) // 2
        yield f"flush={mode} mid+tail", co.compress(data[:mid]) + co.flush(mode) + co.compress(data[mid:]) + co.flush(mode) + co.flush()


rng = random.Random(20261006)


def datasets():
    for n in (1, 2, 3, 7, 255, 256, 257, 1000, 4096, 16383, 16384, 16385, 32767, 32768, 32769, 65535, 65536, 65537, 100000, 262144):
        yield f"random-{n}", rng.randbytes(n), True
        yield f"zeros-{n}", b"\0" * n, True
        yield f"text-{n}", (b"lorem ipsum dolor sit amet " * (n // 27 + 1))[:n], True
        yield f"cycle-{n}", (bytes(range(256)) * (n // 256 + 1))[:n], True
    # 마지막 부호가 문자일 때와 일치(거리 · 길이)일 때가 섞이도록 작은 알파벳의 무작위 글 - 길이 1..3000 전부
    for n in range(1, 3001):
        yield f"small-alphabet-{n}", bytes(rng.choice(b"abcab ") for _ in range(n)), False
    cap = 8 * 1024 * 1024
    yield "zeros-cap", b"\0" * cap, False
    yield "random-cap", rng.randbytes(cap), False


mod = load()
cases = 0
rejected = []
direct_not_eof = []
for label, data, full in datasets():
    for kind, blob in streams(data, full):
        cases += 1
        d = zlib.decompressobj()
        out = d.decompress(blob, len(data))
        if not (d.eof and out == data and not d.unconsumed_tail and not d.unused_data):
            direct_not_eof.append((label, kind, d.eof, len(out), len(d.unconsumed_tail)))
        try:
            if mod.inflate(blob, str(len(data))) != data:
                rejected.append((label, kind, "mismatch"))
        except ValueError as exc:
            rejected.append((label, kind, str(exc)))
print("python", sys.version.split()[0], "| zlib", zlib.ZLIB_RUNTIME_VERSION)
print("cases:", cases, "| inflate rejected or mismatched:", len(rejected), rejected[:5])
print("direct decompressobj with max_length == size not at eof:", len(direct_not_eof), direct_not_eof[:5])

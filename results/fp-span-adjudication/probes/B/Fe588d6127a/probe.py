"""Fe588d6127a (D103) - max_length 가 풀린 크기와 정확히 같을 때 eof 가 False 이고 트레일러가 남아 정상 입력이 거부되는가.

선언 크기 = 실제 풀린 크기인 정상 입력을 모양 · 크기 · 압축 수준을 바꿔 가며 inflate 에 넣는다.
- 모양: 0 바이트 반복 (긴 일치) · 무작위 (저장 블록) · 문장 반복 · bytes(range(256)) 반복
- 크기: 1 · 2 · 255 · 256 · 257 · 16383 · 16384 (CPython 의 첫 출력 버퍼) · 16385 · 32768 · 65536 · 65537 · 1 MiB · 8 MiB (상한)
- 압축 수준: 0 (저장) · 1 · 6 · 9, 그리고 wbits 를 바꾼 스트림은 decoy 가 기본 decompressobj 라 zlib 형식만
"""

import importlib.util
import random
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fe588d6127a", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
print("python", sys.version.split()[0], "| zlib", zlib.ZLIB_RUNTIME_VERSION)
rng = random.Random(20261006)
sizes = [1, 2, 255, 256, 257, 16383, 16384, 16385, 32768, 65536, 65537, 1 << 20, 8 * 1024 * 1024]
shapes = {
    "zeros": lambda n: b"\0" * n,
    "random": lambda n: rng.randbytes(n),
    "text": lambda n: (b"the quick brown fox jumps over the lazy dog. " * (n // 45 + 1))[:n],
    "range": lambda n: (bytes(range(256)) * (n // 256 + 1))[:n],
}
tried = rejected = 0
for shape, make in shapes.items():
    for n in sizes:
        data = make(n)
        for level in (0, 1, 6, 9):
            blob = zlib.compress(data, level)
            tried += 1
            try:
                ok = mod.inflate(blob, str(n)) == data
            except ValueError as exc:
                rejected += 1
                print(f"REJECTED shape={shape} n={n} level={level}: {exc}")
                continue
            if not ok:
                print(f"WRONG OUTPUT shape={shape} n={n} level={level}")

# 같은 경우를 decompressobj 로 직접 보아 eof · 꼬리를 적는다 (대표 몇 개)
for shape in ("zeros", "random", "text"):
    for n in (16384, 65537):
        data = shapes[shape](n)
        d = zlib.decompressobj()
        out = d.decompress(zlib.compress(data, 9), n)
        print(f"direct shape={shape} n={n}: len={len(out)} eof={d.eof} tail={len(d.unconsumed_tail)} unused={len(d.unused_data)}")
print(f"tried={tried} rejected={rejected}")

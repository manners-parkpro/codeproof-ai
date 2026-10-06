"""Fe588d6127a (D103) 보강 - zlib.compress 가 아닌 방식으로 만든 정상 zlib 스트림 (끝 앞의 빈 저장 블록 · 작은 창 · 전략 · 여러 조각).

출력이 꽉 차는 순간 뒤에 출력 없는 블록 (동기 · 완전 플러시가 남기는 빈 저장 블록) 과 트레일러가 남는 스트림이다.
"""

import importlib.util
import random
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_Fe588d6127a_v", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
rng = random.Random(7)
datas = {"text": b"lorem ipsum dolor sit amet " * 3000, "random": rng.randbytes(70001), "one": b"x", "zeros": b"\0" * 300000}
strategies = [zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED, zlib.Z_HUFFMAN_ONLY, zlib.Z_RLE, zlib.Z_FIXED]
tried = rejected = 0
for name, data in datas.items():
    for wbits in (9, 12, 15):
        for strategy in strategies:
            for flush_mode in (None, zlib.Z_SYNC_FLUSH, zlib.Z_FULL_FLUSH):
                for chunks in (1, 3):
                    c = zlib.compressobj(6, zlib.DEFLATED, wbits, 8, strategy)
                    step = max(1, len(data) // chunks)
                    parts = []
                    for i in range(0, len(data), step):
                        parts.append(c.compress(data[i:i + step]))
                        if flush_mode is not None:
                            parts.append(c.flush(flush_mode))
                    parts.append(c.flush())
                    blob = b"".join(parts)
                    tried += 1
                    try:
                        if mod.inflate(blob, str(len(data))) != data:
                            print("WRONG", name, wbits, strategy, flush_mode, chunks)
                    except ValueError as exc:
                        rejected += 1
                        print(f"REJECTED {name} wbits={wbits} strategy={strategy} flush={flush_mode} chunks={chunks}: {exc}")
print(f"tried={tried} rejected={rejected}")

"""F385ddfd244 (D037) - fsync 없이 replace 하는 것이 이 모듈의 입력 · 동기 실패로 관측되는 결함을 만드는가.

지적은 전원 차단 · 커널 충돌 뒤의 내구성이다. 그 상황은 실행으로 만들 수 없다 - 여기서는
(1) 이 코드가 fsync 를 부르지 않는다는 사실과 (2) 프로세스가 살아 있는 동안에는 옛 내용이나 새 내용만
보인다는 것(주장 · 근거의 원자성)을 확인한다. 작업 폴더 안의 임시 디렉터리에서만 쓴다.
"""

import importlib.util
import os
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("decoy_F385ddfd244", HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
print("python", sys.version.split()[0])

# (1) fsync 호출을 관찰만 한다 (결과는 진짜 함수의 것)
calls = []
real_fsync = os.fsync


def watched(fd):
    calls.append(fd)
    return real_fsync(fd)


os.fsync = watched
try:
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        target = Path(tmp) / "config.toml"
        mod.save(target, "a = 1\n")
        mod.save(target, "a = 2\n")
        print("fsync calls during two saves:", len(calls))

        # (2) 살아 있는 프로세스에서 읽는 쪽은 옛 내용 · 새 내용만 본다
        old, new = "x" * 50000 + "\n", "y" * 50000 + "\n"
        mod.save(target, old)
        seen = set()
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                try:
                    seen.add(target.read_text(encoding="utf-8"))
                except FileNotFoundError:
                    seen.add("<missing>")

        t = threading.Thread(target=reader)
        t.start()
        for i in range(200):
            mod.save(target, new if i % 2 == 0 else old)
        stop.set()
        t.join()
        print("states seen by a concurrent reader:", sorted({"old" if s == old else "new" if s == new else repr(s[:20]) for s in seen}))
finally:
    os.fsync = real_fsync

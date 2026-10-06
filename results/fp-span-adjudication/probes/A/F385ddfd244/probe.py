"""F385ddfd244 (D037) - fsync 없이 replace 하는가, 그리고 프로세스 안에서 관측되는 결과가 달라지는가.

네트워크 · 외부 프로그램 없음. 쓰기는 이 폴더 아래 임시 디렉터리에만 한다. os.fsync 를 감싸는 것은 관찰용이다.
전원 상실 · 커널 크래시는 실행할 수 없다 - 그 경로는 basis 에 적는다.
"""

import importlib.util
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str = "d037f_copy"):
    spec = importlib.util.spec_from_file_location(name, HERE / "decoy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mod = load()
calls: list[str] = []
real_fsync, real_fdatasync = os.fsync, getattr(os, "fdatasync", None)
os.fsync = lambda fd: (calls.append("fsync"), real_fsync(fd))[1]
if real_fdatasync is not None:
    os.fdatasync = lambda fd: (calls.append("fdatasync"), real_fdatasync(fd))[1]
try:
    with tempfile.TemporaryDirectory(dir=HERE) as tmp:
        target = pathlib.Path(tmp) / "config.toml"
        sizes = []
        for _ in range(5):
            mod.save(target, "retries = 3\n")
            sizes.append(target.stat().st_size)
        print("sizes after 5 saves:", sizes, "| content:", repr(target.read_text(encoding="utf-8")))
        print("leftover files:", sorted(p.name for p in pathlib.Path(tmp).iterdir()))
finally:
    os.fsync = real_fsync
    if real_fdatasync is not None:
        os.fdatasync = real_fdatasync
print("fsync/fdatasync calls during saves:", calls)
